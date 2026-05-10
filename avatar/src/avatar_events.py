from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AvatarEventKind(str, Enum):
    LISTENING_STARTED = "listening_started"
    THINKING_STARTED = "thinking_started"
    COMMAND_STARTED = "command_started"
    COMMAND_SUCCEEDED = "command_succeeded"
    COMMAND_REJECTED = "command_rejected"
    COMMAND_FAILED = "command_failed"
    SPEAKING_STARTED = "speaking_started"
    SPEAKING_FINISHED = "speaking_finished"
    SPEAKING_LEVEL_CHANGED = "speaking_level_changed"
    RESET_TO_IDLE = "reset_to_idle"


@dataclass(frozen=True)
class AvatarEvent:
    kind: AvatarEventKind
    message: str | None = None
    detail: str | None = None
    amplitude: float | None = None
