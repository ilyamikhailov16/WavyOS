from __future__ import annotations

import time
from dataclasses import replace
from typing import Callable

from .avatar_events import AvatarEvent, AvatarEventKind
from .avatar_lipsync import AvatarLipSync
from .avatar_state import AvatarMode, AvatarSnapshot


class AvatarController:
    """State machine for the avatar runtime."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
        lipsync: AvatarLipSync | None = None,
        idle_status_text: str = "Жду команд",
        listening_status_text: str = "Слушаю",
        thinking_status_text: str = "Думаю",
        executing_status_text: str = "Выполняю",
        speaking_status_text: str = "Отвечаю",
        success_status_text: str = "Готово",
        unknown_status_text: str = "Команда не распознана",
        error_status_text: str = "Произошла ошибка",
        transient_state_seconds: float = 1.5,
        error_state_seconds: float = 3.0,
    ) -> None:
        self.clock = clock or time.monotonic
        self.lipsync = lipsync or AvatarLipSync()
        self.idle_status_text = idle_status_text
        self.listening_status_text = listening_status_text
        self.thinking_status_text = thinking_status_text
        self.executing_status_text = executing_status_text
        self.speaking_status_text = speaking_status_text
        self.success_status_text = success_status_text
        self.unknown_status_text = unknown_status_text
        self.error_status_text = error_status_text
        self.transient_state_seconds = transient_state_seconds
        self.error_state_seconds = error_state_seconds
        self._transient_until: float | None = None
        self._snapshot = AvatarSnapshot(
            mode=AvatarMode.IDLE,
            status_text=self.idle_status_text,
        )

    @property
    def snapshot(self) -> AvatarSnapshot:
        return self._snapshot

    def handle_event(self, event: AvatarEvent) -> AvatarSnapshot:
        now = self.clock()

        if event.kind == AvatarEventKind.LISTENING_STARTED:
            return self._set_mode(
                AvatarMode.LISTENING,
                event.message or self.listening_status_text,
                detail=event.detail,
            )

        if event.kind == AvatarEventKind.THINKING_STARTED:
            return self._set_mode(
                AvatarMode.THINKING,
                event.message or self.thinking_status_text,
                detail=event.detail,
            )

        if event.kind == AvatarEventKind.COMMAND_STARTED:
            return self._set_mode(
                AvatarMode.EXECUTING,
                event.message or self.executing_status_text,
                detail=event.detail,
            )

        if event.kind == AvatarEventKind.COMMAND_SUCCEEDED:
            return self._set_mode(
                AvatarMode.IDLE,
                event.message or self.success_status_text,
                detail=event.detail,
                transient_until=now + self.transient_state_seconds,
            )

        if event.kind == AvatarEventKind.COMMAND_REJECTED:
            return self._set_mode(
                AvatarMode.ERROR,
                event.message or self.unknown_status_text,
                detail=event.detail,
                transient_until=now + self.error_state_seconds,
            )

        if event.kind == AvatarEventKind.COMMAND_FAILED:
            return self._set_mode(
                AvatarMode.ERROR,
                event.message or self.error_status_text,
                detail=event.detail,
                transient_until=now + self.error_state_seconds,
            )

        if event.kind == AvatarEventKind.SPEAKING_STARTED:
            return self._set_mode(
                AvatarMode.SPEAKING,
                event.message or self.speaking_status_text,
                detail=event.detail,
            )

        if event.kind == AvatarEventKind.SPEAKING_FINISHED:
            return self._set_mode(AvatarMode.IDLE, self.idle_status_text)

        if event.kind == AvatarEventKind.SPEAKING_LEVEL_CHANGED:
            if self._snapshot.mode != AvatarMode.SPEAKING:
                return self._snapshot
            mouth_level = self.lipsync.level_from_amplitude(event.amplitude)
            return self._replace_snapshot(mouth_level=mouth_level)

        if event.kind == AvatarEventKind.RESET_TO_IDLE:
            return self._set_mode(AvatarMode.IDLE, event.message or self.idle_status_text)

        return self._snapshot

    def tick(self) -> AvatarSnapshot:
        now = self.clock()

        if (
            self._transient_until is not None
            and now >= self._transient_until
            and self._snapshot.mode != AvatarMode.SPEAKING
        ):
            return self._set_mode(AvatarMode.IDLE, self.idle_status_text)

        if self._snapshot.mode == AvatarMode.SPEAKING:
            return self._replace_snapshot(mouth_level=self.lipsync.pulse_level(now))

        if self._snapshot.mouth_level != 0:
            return self._replace_snapshot(mouth_level=0)

        return self._snapshot

    def _set_mode(
        self,
        mode: AvatarMode,
        status_text: str,
        *,
        detail: str | None = None,
        transient_until: float | None = None,
    ) -> AvatarSnapshot:
        self._transient_until = transient_until
        self._snapshot = AvatarSnapshot(
            mode=mode,
            status_text=status_text,
            detail=detail,
            mouth_level=0,
        )
        return self._snapshot

    def _replace_snapshot(self, **changes: object) -> AvatarSnapshot:
        self._snapshot = replace(self._snapshot, **changes)
        return self._snapshot
