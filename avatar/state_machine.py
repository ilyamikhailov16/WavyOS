from __future__ import annotations

import logging
from enum import Enum
from typing import Callable

from app_logging import get_logger

logger: logging.Logger = get_logger(__name__)


class AvatarState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"


_ALLOWED_TRANSITIONS: dict[AvatarState, frozenset[AvatarState]] = {
    AvatarState.IDLE:      frozenset({AvatarState.LISTENING, AvatarState.ERROR}),
    AvatarState.LISTENING: frozenset({AvatarState.THINKING, AvatarState.IDLE, AvatarState.ERROR}),
    AvatarState.THINKING:  frozenset({AvatarState.EXECUTING, AvatarState.IDLE, AvatarState.ERROR}),
    AvatarState.EXECUTING: frozenset({AvatarState.SPEAKING, AvatarState.ERROR}),
    AvatarState.SPEAKING:  frozenset({AvatarState.IDLE, AvatarState.ERROR}),
    AvatarState.ERROR:     frozenset({AvatarState.IDLE}),
}

StateChangeCallback = Callable[[AvatarState, AvatarState], None]


class AvatarStateMachine:
    """Engine-agnostic avatar state machine with explicit transition guards."""

    def __init__(self) -> None:
        self._state: AvatarState = AvatarState.IDLE
        self._callbacks: list[StateChangeCallback] = []

    def getState(self) -> AvatarState:
        return self._state

    def setState(self, new_state: AvatarState) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            logger.warning(
                "Invalid transition %s → %s ignored",
                self._state.value,
                new_state.value,
            )
            return

        old_state = self._state
        self._state = new_state
        logger.debug("Avatar state: %s → %s", old_state.value, new_state.value)

        for cb in list(self._callbacks):
            try:
                cb(old_state, new_state)
            except Exception:
                logger.exception("State change callback raised an exception")

    def onStateChange(self, callback: StateChangeCallback) -> None:
        self._callbacks.append(callback)
