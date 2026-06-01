from avatar.src.avatar_controller import AvatarController
from avatar.src.avatar_events import AvatarEvent, AvatarEventKind
from avatar.src.avatar_state import AvatarMode


class FakeClock:
    def __init__(self) -> None:
        self.current = 100.0

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def test_avatar_controller_drives_main_state_flow() -> None:
    clock = FakeClock()
    controller = AvatarController(clock=clock)

    assert controller.snapshot.mode == AvatarMode.IDLE

    controller.handle_event(AvatarEvent(kind=AvatarEventKind.LISTENING_STARTED))
    assert controller.snapshot.mode == AvatarMode.LISTENING

    controller.handle_event(AvatarEvent(kind=AvatarEventKind.THINKING_STARTED))
    assert controller.snapshot.mode == AvatarMode.THINKING

    controller.handle_event(
        AvatarEvent(kind=AvatarEventKind.COMMAND_STARTED, detail="Открой сайт")
    )
    assert controller.snapshot.mode == AvatarMode.EXECUTING
    assert controller.snapshot.detail == "Открой сайт"


def test_avatar_controller_returns_to_idle_after_success_timeout() -> None:
    clock = FakeClock()
    controller = AvatarController(clock=clock, transient_state_seconds=1.0)

    controller.handle_event(AvatarEvent(kind=AvatarEventKind.COMMAND_SUCCEEDED))
    assert controller.snapshot.mode == AvatarMode.IDLE
    assert controller.snapshot.status_text == "Готово"

    clock.advance(1.1)
    controller.tick()
    assert controller.snapshot.mode == AvatarMode.IDLE
    assert controller.snapshot.status_text == "Жду команд"


def test_avatar_controller_shows_error_then_recovers() -> None:
    clock = FakeClock()
    controller = AvatarController(clock=clock, error_state_seconds=2.0)

    controller.handle_event(
        AvatarEvent(
            kind=AvatarEventKind.COMMAND_FAILED,
            message="Ошибка выполнения",
            detail="boom",
        )
    )

    assert controller.snapshot.mode == AvatarMode.ERROR
    assert controller.snapshot.detail == "boom"

    clock.advance(2.1)
    controller.tick()
    assert controller.snapshot.mode == AvatarMode.IDLE
    assert controller.snapshot.status_text == "Жду команд"


def test_avatar_controller_supports_simple_speaking_lipsync() -> None:
    clock = FakeClock()
    controller = AvatarController(clock=clock)

    controller.handle_event(AvatarEvent(kind=AvatarEventKind.SPEAKING_STARTED))
    assert controller.snapshot.mode == AvatarMode.SPEAKING

    controller.handle_event(
        AvatarEvent(
            kind=AvatarEventKind.SPEAKING_LEVEL_CHANGED,
            amplitude=0.7,
        )
    )
    assert controller.snapshot.mouth_level == 2

    controller.handle_event(AvatarEvent(kind=AvatarEventKind.SPEAKING_FINISHED))
    assert controller.snapshot.mode == AvatarMode.IDLE
    assert controller.snapshot.mouth_level == 0
