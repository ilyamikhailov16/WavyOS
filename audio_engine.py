import threading
from typing import Callable, List

import numpy as np
import sounddevice as sd


class AudioEngine:
    
    def __init__(
        self,
        samplerate: int = 44100,
        blocksize: int = 1024,
        channels: int = 1,
        gain: float = 35.0,
        smoothing: float = 0.75,
        device=None,
    ):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.channels = channels
        self.gain = gain
        self.smoothing = smoothing
        self.device = device

        self._listeners: List[Callable[[float, float], None]] = []
        self._lock = threading.Lock()

        self._stream = None
        self._running = False

        self._smooth_volume = 0.0
        self._prev_volume = 0.0

    def subscribe(self, cb: Callable[[float, float], None]):
        with self._lock:
            self._listeners.append(cb)

    def _emit(self, volume: float, energy: float):
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(volume, energy)
            except Exception:
                pass

    def _callback(self, indata, frames, time_info, status):
        try:
            rms = float(np.sqrt(np.mean(np.square(indata))))
        except Exception:
            rms = 0.0

        raw = rms * self.gain

        a = self.smoothing
        self._smooth_volume = self._smooth_volume * a + raw * (1.0 - a)

        energy = abs(self._smooth_volume - self._prev_volume) * 5.0
        self._prev_volume = self._smooth_volume

        volume = max(0.0, min(1.0, self._smooth_volume))
        self._emit(volume, energy)

    def start(self):
        if self._running:
            return
        self._stream = sd.InputStream(
            callback=self._callback,
            channels=self.channels,
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=self.device,
        )
        self._stream.start()
        self._running = True

    def stop(self):
        if not self._running:
            return
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass
        finally:
            self._stream = None
            self._running = False
