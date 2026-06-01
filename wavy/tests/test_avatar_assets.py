from pathlib import Path

from PIL import Image, ImageChops

from avatar.src.avatar_renderer import (
    AvatarAssetManifest,
    LayeredAvatarComposer,
    TkAvatarRenderer,
)
from avatar.src.avatar_state import AvatarMode, AvatarSnapshot


ASSETS_DIR = Path("avatar/assets")
MANIFEST_PATH = ASSETS_DIR / "avatar_manifest.json"


def _load_manifest() -> AvatarAssetManifest:
    return AvatarAssetManifest.load(MANIFEST_PATH, ASSETS_DIR)


def test_layered_avatar_composer_matches_idle_complete_asset() -> None:
    manifest = _load_manifest()
    composer = LayeredAvatarComposer(manifest)

    composed = composer.compose(AvatarSnapshot(AvatarMode.IDLE, "idle"), now=0)
    complete = Image.open(ASSETS_DIR / "IDLE/IDLE_COMPLETE.png").convert("RGBA")

    assert composed.size == (480, 480)
    assert ImageChops.difference(composed, complete).getbbox() is None


def test_layered_avatar_composer_uses_speaking_mouth_level() -> None:
    manifest = _load_manifest()
    composer = LayeredAvatarComposer(manifest)

    closed = composer.compose(
        AvatarSnapshot(AvatarMode.SPEAKING, "speaking", mouth_level=0),
        now=0,
    )
    open_mouth = composer.compose(
        AvatarSnapshot(AvatarMode.SPEAKING, "speaking", mouth_level=2),
        now=0,
    )

    assert ImageChops.difference(closed, open_mouth).convert("RGB").getbbox() is not None


def test_avatar_manifest_covers_every_runtime_mode() -> None:
    manifest = _load_manifest()

    assert set(manifest.states) == set(AvatarMode)
    assert manifest.layers_order == ("hairtie", "eyebrows", "eyes", "mouth")
    assert manifest.base_path.exists()


def test_avatar_manifest_references_existing_png_files() -> None:
    manifest = _load_manifest()

    for state in manifest.states.values():
        for layer in state.layers.values():
            assert layer.frames
            for frame in layer.frames:
                assert frame.exists(), frame
                assert frame.suffix.lower() == ".png"


def test_layered_avatar_composer_matches_static_complete_assets() -> None:
    manifest = _load_manifest()
    composer = LayeredAvatarComposer(manifest)
    complete_assets = {
        AvatarMode.IDLE: ASSETS_DIR / "IDLE/IDLE_COMPLETE.png",
        AvatarMode.LISTENING: ASSETS_DIR / "LISTENING/LISTENING_COMPLETE.png",
        AvatarMode.ERROR: ASSETS_DIR / "ERROR/ERROR_COMPLETE.png",
    }

    for mode, complete_path in complete_assets.items():
        composed = composer.compose(AvatarSnapshot(mode, mode.value), now=0)
        complete = Image.open(complete_path).convert("RGBA")

        assert ImageChops.difference(composed, complete).getbbox() is None


def test_layered_avatar_composer_selects_loop_frames_by_time() -> None:
    manifest = _load_manifest()
    composer = LayeredAvatarComposer(manifest)
    thinking_eyes = manifest.states[AvatarMode.THINKING].layers["eyes"]

    first_frame = composer._select_frame(
        thinking_eyes,
        snapshot=AvatarSnapshot(AvatarMode.THINKING, "thinking"),
        now=0,
    )
    second_frame = composer._select_frame(
        thinking_eyes,
        snapshot=AvatarSnapshot(AvatarMode.THINKING, "thinking"),
        now=manifest.frame_duration_seconds,
    )

    assert first_frame == ASSETS_DIR / "THINKING/THINKING_EYES_0.png"
    assert second_frame == ASSETS_DIR / "THINKING/THINKING_EYES_1.png"


def test_layered_avatar_composer_clamps_speaking_mouth_level() -> None:
    manifest = _load_manifest()
    composer = LayeredAvatarComposer(manifest)
    speaking_mouth = manifest.states[AvatarMode.SPEAKING].layers["mouth"]

    selected = composer._select_frame(
        speaking_mouth,
        snapshot=AvatarSnapshot(AvatarMode.SPEAKING, "speaking", mouth_level=99),
        now=0,
    )

    assert selected == ASSETS_DIR / "SPEAKING/SPEAKING_MOUTH_3.png"


def test_tk_renderer_no_longer_keeps_legacy_canvas_mouth() -> None:
    renderer = TkAvatarRenderer(
        image_path="src/images/mascot.png",
        assets_dir=ASSETS_DIR,
        manifest_path=MANIFEST_PATH,
    )

    assert not hasattr(renderer, "_mouth_canvas")
    assert not hasattr(renderer, "_mouth_rect")
