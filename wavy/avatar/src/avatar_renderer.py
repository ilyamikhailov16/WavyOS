from __future__ import annotations

import json
import queue
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app_logging import get_logger

from .avatar_state import AvatarMode, AvatarSnapshot

logger = get_logger(__name__)


class BaseAvatarRenderer(ABC):
    @abstractmethod
    def start(self, snapshot: AvatarSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def render(self, snapshot: AvatarSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    def process_pending(self) -> None:
        return


class NullAvatarRenderer(BaseAvatarRenderer):
    def __init__(self) -> None:
        self.last_snapshot: AvatarSnapshot | None = None

    def start(self, snapshot: AvatarSnapshot) -> None:
        self.last_snapshot = snapshot

    def render(self, snapshot: AvatarSnapshot) -> None:
        self.last_snapshot = snapshot

    def stop(self) -> None:
        return


@dataclass(frozen=True)
class AvatarLayer:
    name: str
    frames: tuple[Path, ...]


@dataclass(frozen=True)
class AvatarStateLayers:
    layers: dict[str, AvatarLayer]


class AvatarAssetManifest:
    def __init__(
        self,
        *,
        assets_dir: Path,
        base_path: Path,
        layers_order: tuple[str, ...],
        states: dict[AvatarMode, AvatarStateLayers],
        frame_duration_seconds: float,
    ) -> None:
        self.assets_dir = assets_dir
        self.base_path = base_path
        self.layers_order = layers_order
        self.states = states
        self.frame_duration_seconds = frame_duration_seconds

    @classmethod
    def load(cls, manifest_path: str | Path, assets_dir: str | Path) -> "AvatarAssetManifest":
        manifest_path = Path(manifest_path)
        assets_dir = Path(assets_dir)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        states: dict[AvatarMode, AvatarStateLayers] = {}

        for mode in AvatarMode:
            state_raw = raw.get("states", {}).get(mode.value)
            if not state_raw:
                continue

            layers: dict[str, AvatarLayer] = {}
            for layer_name, layer_frames in state_raw.get("layers", {}).items():
                frames = tuple(assets_dir / frame for frame in layer_frames)
                layers[layer_name] = AvatarLayer(name=layer_name, frames=frames)
            states[mode] = AvatarStateLayers(layers=layers)

        return cls(
            assets_dir=assets_dir,
            base_path=assets_dir / raw["base"],
            layers_order=tuple(raw.get("layers_order", ())),
            states=states,
            frame_duration_seconds=float(raw.get("frame_duration_seconds", 0.25)),
        )


class LayeredAvatarComposer:
    def __init__(self, manifest: AvatarAssetManifest) -> None:
        self.manifest = manifest
        self._image_cache: dict[Path, Any] = {}

    def compose(self, snapshot: AvatarSnapshot, *, now: float | None = None) -> Any:
        from PIL import Image

        now = time.monotonic() if now is None else now
        base = self._open_image(self.manifest.base_path).copy()
        state = self.manifest.states.get(snapshot.mode) or self.manifest.states[AvatarMode.IDLE]

        for layer_name in self.manifest.layers_order:
            layer = state.layers.get(layer_name)
            if not layer or not layer.frames:
                continue
            frame_path = self._select_frame(layer, snapshot=snapshot, now=now)
            base.alpha_composite(self._open_image(frame_path))

        return base

    def _select_frame(self, layer: AvatarLayer, *, snapshot: AvatarSnapshot, now: float) -> Path:
        if layer.name == "mouth" and snapshot.mode == AvatarMode.SPEAKING:
            return layer.frames[min(snapshot.mouth_level, len(layer.frames) - 1)]

        if len(layer.frames) == 1:
            return layer.frames[0]

        frame_index = int(now / self.manifest.frame_duration_seconds) % len(layer.frames)
        return layer.frames[frame_index]

    def _open_image(self, path: Path) -> Any:
        from PIL import Image

        if path not in self._image_cache:
            self._image_cache[path] = Image.open(path).convert("RGBA")
        return self._image_cache[path]


class TkAvatarRenderer(BaseAvatarRenderer):
    """Tk renderer that can compose the avatar from layered state assets."""

    STATE_COLORS: dict[AvatarMode, str] = {
        AvatarMode.IDLE: "#4D7C0F",
        AvatarMode.LISTENING: "#0F766E",
        AvatarMode.THINKING: "#1D4ED8",
        AvatarMode.EXECUTING: "#B45309",
        AvatarMode.SPEAKING: "#9333EA",
        AvatarMode.ERROR: "#B91C1C",
    }

    def __init__(
        self,
        *,
        image_path: str | Path,
        assets_dir: str | Path | None = None,
        manifest_path: str | Path | None = None,
        animation_enabled: bool = True,
        on_window_closed: Callable[[], None] | None = None,
        window_title: str = "WavyOS Avatar",
        window_size: tuple[int, int] = (360, 460),
        topmost: bool = True,
    ) -> None:
        self.image_path = Path(image_path)
        self.assets_dir = Path(assets_dir) if assets_dir else None
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self.animation_enabled = animation_enabled
        self.on_window_closed = on_window_closed
        self.window_title = window_title
        self.window_size = window_size
        self.topmost = topmost
        self._queue: queue.Queue[AvatarSnapshot | None] = queue.Queue()
        self._root = None
        self._image_label = None
        self._state_label = None
        self._status_label = None
        self._state_colors = dict(self.STATE_COLORS)
        self._composer: LayeredAvatarComposer | None = None
        self._image_photo = None
        self._current_snapshot: AvatarSnapshot | None = None
        self._display_size: tuple[int, int] = (0, 0)
        self._closed = False

    def start(self, snapshot: AvatarSnapshot) -> None:
        if self._root is not None:
            return
        self._closed = False
        try:
            import tkinter as tk
            from PIL import Image, ImageTk
        except Exception as exc:
            logger.warning("Tk avatar renderer is unavailable: %s", exc)
            return

        try:
            root = tk.Tk()
            root.title(self.window_title)
            root.protocol("WM_DELETE_WINDOW", self._handle_window_closed)
            width, height = self.window_size
            root.geometry(f"{width}x{height}")
            root.resizable(False, False)
            if self.topmost:
                root.attributes("-topmost", True)
            root.configure(bg="#111827")

            frame = tk.Frame(root, bg="#111827", padx=16, pady=16)
            frame.pack(fill="both", expand=True)

            self._composer = self._load_composer()
            image = self._compose_image(snapshot) or Image.open(self.image_path).convert("RGBA")
            image.thumbnail((width - 32, 260))
            self._display_size = image.size

            self._root = root
            self._image_photo = ImageTk.PhotoImage(image, master=root)
            image_label = tk.Label(frame, image=self._image_photo, bg="#111827")
            image_label.pack(pady=(0, 12))

            state_label = tk.Label(
                frame,
                text="IDLE",
                font=("Segoe UI", 16, "bold"),
                bg="#111827",
                fg="#E5E7EB",
            )
            state_label.pack()

            status_label = tk.Label(
                frame,
                text="Жду команд",
                font=("Segoe UI", 11),
                bg="#111827",
                fg="#CBD5E1",
                wraplength=width - 48,
                justify="center",
            )
            status_label.pack(pady=(8, 10))

            self._image_label = image_label
            self._state_label = state_label
            self._status_label = status_label
            self.render(snapshot)
            self.process_pending()
        except Exception as exc:
            logger.warning("Tk avatar renderer failed to start: %s", exc)
            self._clear_widgets()

    def render(self, snapshot: AvatarSnapshot) -> None:
        if self._closed:
            return
        self._queue.put(snapshot)

    def stop(self) -> None:
        self._closed = True
        if self._root is None:
            self._clear_widgets()
            return
        try:
            self._root.destroy()
        except Exception as exc:
            logger.warning("Tk avatar renderer failed to stop cleanly: %s", exc)
        finally:
            self._clear_widgets()

    def _handle_window_closed(self) -> None:
        self.stop()
        if self.on_window_closed is not None:
            try:
                self.on_window_closed()
            except Exception:
                logger.exception("Exception in avatar window close callback")

    def process_pending(self) -> None:
        if self._closed or self._root is None:
            return
        updated = False
        try:
            while True:
                item = self._queue.get_nowait()
                if item is None:
                    break
                self._apply_snapshot(item)
                updated = True
        except queue.Empty:
            pass
        except Exception as exc:
            logger.warning("Tk avatar renderer stopped after UI update failure: %s", exc)
            self.stop()
            return

        if self.animation_enabled and not updated and self._current_snapshot is not None:
            try:
                self._apply_avatar_image(self._current_snapshot)
            except Exception as exc:
                logger.warning("Tk avatar renderer stopped after animation failure: %s", exc)
                self.stop()
                return

        try:
            self._root.update_idletasks()
            self._root.update()
        except Exception as exc:
            logger.warning("Tk avatar renderer stopped after root update failure: %s", exc)
            self.stop()
            return

    def _apply_snapshot(self, snapshot: AvatarSnapshot) -> None:
        if (
            self._state_label is None
            or self._status_label is None
        ):
            return

        self._current_snapshot = snapshot
        self._apply_avatar_image(snapshot)
        self._state_label.configure(
            text=snapshot.mode.value.upper(),
            fg=self._state_colors.get(snapshot.mode, "#E5E7EB"),
        )
        self._status_label.configure(text=snapshot.detail or snapshot.status_text)

    def _load_composer(self) -> LayeredAvatarComposer | None:
        if self.assets_dir is None or self.manifest_path is None:
            return None
        if not self.assets_dir.exists() or not self.manifest_path.exists():
            logger.warning("Avatar layered assets are missing; falling back to %s", self.image_path)
            return None
        try:
            return LayeredAvatarComposer(
                AvatarAssetManifest.load(
                    manifest_path=self.manifest_path,
                    assets_dir=self.assets_dir,
                )
            )
        except Exception as exc:
            logger.warning("Avatar manifest could not be loaded: %s", exc)
            return None

    def _compose_image(self, snapshot: AvatarSnapshot) -> Any | None:
        if self._composer is None:
            return None
        try:
            return self._composer.compose(snapshot)
        except Exception as exc:
            logger.warning("Avatar layered image could not be composed: %s", exc)
            return None

    def _apply_avatar_image(self, snapshot: AvatarSnapshot) -> None:
        if self._closed or self._root is None or self._image_label is None:
            return
        image = self._compose_image(snapshot)
        if image is None:
            return
        if self._display_size != (0, 0):
            image = image.copy()
            image.thumbnail(self._display_size)

        from PIL import ImageTk

        self._image_photo = ImageTk.PhotoImage(image, master=self._root)
        self._image_label.configure(image=self._image_photo)

    def _clear_widgets(self) -> None:
        self._root = None
        self._image_label = None
        self._state_label = None
        self._status_label = None
        self._composer = None
        self._image_photo = None
        self._current_snapshot = None
