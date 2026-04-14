from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AvatarMode(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True)
class AvatarSnapshot:
    mode: AvatarMode
    status_text: str
    mouth_level: int = 0
    detail: str | None = None
