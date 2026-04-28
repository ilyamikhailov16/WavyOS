from dataclasses import dataclass, asdict
from typing import Callable, List
import threading
import time


@dataclass
class AvatarState:
    state: str = "idle"           
    expression: str = "neutral"  
    speak_level: float = 0.0      
    energy: float = 0.0          
    updated_at: float = 0.0


class AvatarController:
    

    def __init__(self):
        self._data = AvatarState(updated_at=time.time())
        self._listeners: List[Callable[[dict], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, cb: Callable[[dict], None]):
        with self._lock:
            self._listeners.append(cb)

    def _emit(self):
        self._data.updated_at = time.time()
        payload = asdict(self._data)
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(payload)
            except Exception:
                pass

    def set_state(self, v: str):
        if self._data.state != v:
            self._data.state = v
            self._emit()

    def set_expression(self, v: str):
        if self._data.expression != v:
            self._data.expression = v
            self._emit()

    def speak_level(self, v: float):
        self._data.speak_level = max(0.0, min(1.0, float(v)))
        self._emit()

    def set_energy(self, v: float):
        self._data.energy = max(0.0, float(v))
        self._emit()

    def get(self) -> dict:
        return asdict(self._data)

    def get_snapshot(self) -> dict:
        return asdict(self._data)
