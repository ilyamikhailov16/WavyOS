import time

from avatar.src.avatar_controller import AvatarController
from avatar.src.avatar_renderer import NullAvatarRenderer
from avatar.src.avatar_service import AvatarService
from avatar.src.avatar_state import AvatarMode


def _wait_for(predicate, timeout: float = 1.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for predicate")


def test_avatar_service_dispatches_stt_and_command_events() -> None:
    renderer = NullAvatarRenderer()
    service = AvatarService(
        controller=AvatarController(),
        renderer=renderer,
        tick_interval_s=0.02,
    )

    service.start()
    try:
        service.handle_stt_status("listening_started")
        _wait_for(
            lambda: renderer.last_snapshot is not None
            and renderer.last_snapshot.mode == AvatarMode.LISTENING
        )
        assert renderer.last_snapshot.mode == AvatarMode.LISTENING

        service.handle_stt_status("transcription_started")
        _wait_for(lambda: renderer.last_snapshot.mode == AvatarMode.THINKING)
        assert renderer.last_snapshot.mode == AvatarMode.THINKING

        service.on_command_started("Открой сайт")
        _wait_for(lambda: renderer.last_snapshot.mode == AvatarMode.EXECUTING)
        assert renderer.last_snapshot.detail == "Открой сайт"

        service.on_command_succeeded("Открой сайт")
        _wait_for(lambda: renderer.last_snapshot.status_text == "Команда выполнена")
        assert renderer.last_snapshot.mode == AvatarMode.IDLE
    finally:
        service.stop()
