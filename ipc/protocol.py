"""
Shared message protocol for IPC between core/gui/tray.
All messages are JSON-serializable dataclasses.
"""
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum, auto


@dataclass
class SttStatusMessage:
    """Broadcast message: just a string status + metadata."""
    msg_id: str
    status: str  # ← Строка, которую понимает avatar_service.handle_stt_status
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> 'SttStatusMessage':
        data = json.loads(raw)
        return cls(**data)

class MessageType(Enum):
    REQUEST = auto()
    RESPONSE = auto()
    EVENT = auto()
    ERROR = auto()


class Command(Enum):
    # === Tray → GUI ===
    OPEN_SETTINGS = "open_settings"
    SHUTDOWN = "shutdown"

    # === GUI → Core ===
    LAUNCH_APP = "launch_app"
    CLOSE_APP = "close_app"
    UNINSTALL_APP = "uninstall_app"
    LIST_RUNNING_APPS = "list_running_apps"
    IS_APP_RUNNING = "is_app_running"

    # === Core → GUI (events, fire-and-forget) ===
    TTS_STARTED = "tts_started"
    TTS_FINISHED = "tts_finished"
    STT_STATUS = "stt_status"
    COMMAND_EXECUTED = "command_executed"


@dataclass
class Message:
    msg_id: str
    msg_type: MessageType
    command: Optional[Command] = None
    payload: dict = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())

    def to_json(self) -> str:
        data = asdict(self)
        data['msg_type'] = self.msg_type.name
        if self.command:
            data['command'] = self.command.value
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> 'Message':
        data = json.loads(raw)
        data['msg_type'] = MessageType[data['msg_type']]
        if data.get('command'):
            data['command'] = Command(data['command'])
        return cls(**data)

    def __repr__(self) -> str:
        return f"Message({self.command}, {self.msg_type.name}, id={self.msg_id})"