from __future__ import annotations

import queue
import threading
from app_logging import get_logger
from config import settings

from .avatar_controller import AvatarController
from .avatar_events import AvatarEvent, AvatarEventKind
from .avatar_renderer import BaseAvatarRenderer, NullAvatarRenderer, TkAvatarRenderer

logger = get_logger(__name__)


class AvatarService:
    """Thread-safe façade used by the app and STT pipeline."""

    def __init__(
        self,
        controller: AvatarController,
        renderer: BaseAvatarRenderer,
        *,
        tick_interval_s: float = 0.15,
    ) -> None:
        self.controller = controller
        self.renderer = renderer
        self.tick_interval_s = tick_interval_s
        self._events: queue.Queue[AvatarEvent] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.renderer.start(self.controller.snapshot)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="avatar-service",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self.renderer.stop()

    def process_ui_events(self) -> None:
        self.renderer.process_pending()

    def handle_stt_status(self, status: str) -> None:
        mapping = {
            "listening_started": AvatarEventKind.LISTENING_STARTED,
            "recording_stopped": AvatarEventKind.THINKING_STARTED,
            "transcription_started": AvatarEventKind.THINKING_STARTED,
            "processing_error": AvatarEventKind.COMMAND_FAILED,
        }
        kind = mapping.get(status)
        if not kind:
            return
        self.emit(AvatarEvent(kind=kind))

    def on_command_started(self, command_name: str) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.COMMAND_STARTED,
                message="Выполняю команду",
                detail=command_name,
            )
        )

    def on_command_succeeded(self, command_name: str) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.COMMAND_SUCCEEDED,
                message="Команда выполнена",
                detail=command_name,
            )
        )

    def on_command_rejected(self) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.COMMAND_REJECTED,
                message="Не удалось распознать команду",
            )
        )

    def on_command_failed(self, error_message: str) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.COMMAND_FAILED,
                message="Ошибка выполнения",
                detail=error_message,
            )
        )

    def on_speaking_started(self, message: str | None = None) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.SPEAKING_STARTED,
                message=message,
            )
        )

    def on_speaking_level(self, amplitude: float) -> None:
        self.emit(
            AvatarEvent(
                kind=AvatarEventKind.SPEAKING_LEVEL_CHANGED,
                amplitude=amplitude,
            )
        )

    def on_speaking_finished(self) -> None:
        self.emit(AvatarEvent(kind=AvatarEventKind.SPEAKING_FINISHED))

    def reset_to_idle(self) -> None:
        self.emit(AvatarEvent(kind=AvatarEventKind.RESET_TO_IDLE))

    def emit(self, event: AvatarEvent) -> None:
        self._events.put(event)

    def _run_loop(self) -> None:
        last_snapshot = self.controller.snapshot
        while not self._stop_event.is_set():
            try:
                event = self._events.get(timeout=self.tick_interval_s)
            except queue.Empty:
                snapshot = self.controller.tick()
            else:
                snapshot = self.controller.handle_event(event)

            if snapshot != last_snapshot:
                self.renderer.render(snapshot)
                last_snapshot = snapshot


def build_avatar_service() -> AvatarService:
    avatar_cfg = settings.avatar
    controller = AvatarController(
        idle_status_text=avatar_cfg.idle_status_text,
        listening_status_text=avatar_cfg.listening_status_text,
        thinking_status_text=avatar_cfg.thinking_status_text,
        executing_status_text=avatar_cfg.executing_status_text,
        speaking_status_text=avatar_cfg.speaking_status_text,
        success_status_text=avatar_cfg.success_status_text,
        unknown_status_text=avatar_cfg.unknown_status_text,
        error_status_text=avatar_cfg.error_status_text,
        transient_state_seconds=avatar_cfg.transient_state_seconds,
        error_state_seconds=avatar_cfg.error_state_seconds,
    )

    renderer: BaseAvatarRenderer
    if avatar_cfg.enabled:
        renderer = TkAvatarRenderer(
            image_path=avatar_cfg.image_path,
            window_title=avatar_cfg.window_title,
            window_size=(avatar_cfg.window_width, avatar_cfg.window_height),
            topmost=avatar_cfg.topmost,
        )
    else:
        renderer = NullAvatarRenderer()

    return AvatarService(
        controller=controller,
        renderer=renderer,
        tick_interval_s=avatar_cfg.tick_interval_seconds,
    )
