from __future__ import annotations

import queue
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from app_logging import get_logger

from .avatar_state import AvatarMode, AvatarSnapshot

logger = get_logger(__name__)


class BaseAvatarRenderer(ABC):
    @abstractmethod
    def start(self, snapshot: AvatarSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def render(self, snapshot: AvatarSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class NullAvatarRenderer(BaseAvatarRenderer):
    def __init__(self) -> None:
        self.last_snapshot: AvatarSnapshot | None = None

    def start(self, snapshot: AvatarSnapshot) -> None:
        self.last_snapshot = snapshot

    def render(self, snapshot: AvatarSnapshot) -> None:
        self.last_snapshot = snapshot

    def stop(self) -> None:
        return


class TkAvatarRenderer(BaseAvatarRenderer):
    """Simple sprite-based MVP renderer using the existing mascot asset."""

    STATE_COLORS: dict[AvatarMode, str] = {
        AvatarMode.IDLE: "#4D7C0F",
        AvatarMode.LISTENING: "#0F766E",
        AvatarMode.THINKING: "#1D4ED8",
        AvatarMode.EXECUTING: "#B45309",
        AvatarMode.SPEAKING: "#9333EA",
        AvatarMode.ERROR: "#B91C1C",
    }

    def __init__(
        self,
        *,
        image_path: str | Path,
        window_title: str = "WavyOS Avatar",
        window_size: tuple[int, int] = (360, 460),
        topmost: bool = True,
    ) -> None:
        self.image_path = Path(image_path)
        self.window_title = window_title
        self.window_size = window_size
        self.topmost = topmost
        self._queue: queue.Queue[AvatarSnapshot | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def start(self, snapshot: AvatarSnapshot) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._run_window,
            name="avatar-renderer",
            daemon=True,
        )
        self._thread.start()
        self._started.wait(timeout=3)
        self.render(snapshot)

    def render(self, snapshot: AvatarSnapshot) -> None:
        self._queue.put(snapshot)

    def stop(self) -> None:
        if not self._thread:
            return
        self._queue.put(None)
        self._thread.join(timeout=3)

    def _run_window(self) -> None:
        try:
            import tkinter as tk
            from PIL import Image, ImageTk
        except Exception as exc:
            logger.warning("Tk avatar renderer is unavailable: %s", exc)
            self._started.set()
            return

        try:
            root = tk.Tk()
            root.title(self.window_title)
            width, height = self.window_size
            root.geometry(f"{width}x{height}")
            root.resizable(False, False)
            if self.topmost:
                root.attributes("-topmost", True)
            root.configure(bg="#111827")

            frame = tk.Frame(root, bg="#111827", padx=16, pady=16)
            frame.pack(fill="both", expand=True)

            image = Image.open(self.image_path).convert("RGBA")
            image.thumbnail((width - 32, 260))
            image_photo = ImageTk.PhotoImage(image)

            image_label = tk.Label(frame, image=image_photo, bg="#111827")
            image_label.image = image_photo
            image_label.pack(pady=(0, 12))

            state_label = tk.Label(
                frame,
                text="IDLE",
                font=("Segoe UI", 16, "bold"),
                bg="#111827",
                fg="#E5E7EB",
            )
            state_label.pack()

            status_label = tk.Label(
                frame,
                text="Жду команд",
                font=("Segoe UI", 11),
                bg="#111827",
                fg="#CBD5E1",
                wraplength=width - 48,
                justify="center",
            )
            status_label.pack(pady=(8, 10))

            mouth_canvas = tk.Canvas(
                frame,
                width=120,
                height=28,
                bg="#111827",
                highlightthickness=0,
            )
            mouth_canvas.pack()
            mouth_rect = mouth_canvas.create_rectangle(
                20, 10, 100, 18, fill="#E5E7EB", outline=""
            )

            def apply_snapshot(snapshot: AvatarSnapshot) -> None:
                state_label.configure(
                    text=snapshot.mode.value.upper(),
                    fg=self.STATE_COLORS.get(snapshot.mode, "#E5E7EB"),
                )
                status_label.configure(text=snapshot.detail or snapshot.status_text)
                mouth_height = {0: 6, 1: 12, 2: 18}.get(snapshot.mouth_level, 6)
                mouth_canvas.coords(
                    mouth_rect,
                    20,
                    14 - (mouth_height // 2),
                    100,
                    14 + (mouth_height // 2),
                )
                mouth_canvas.itemconfigure(
                    mouth_rect,
                    fill=self.STATE_COLORS.get(snapshot.mode, "#E5E7EB"),
                )

            def pump_queue() -> None:
                try:
                    while True:
                        item = self._queue.get_nowait()
                        if item is None:
                            root.destroy()
                            return
                        apply_snapshot(item)
                except queue.Empty:
                    pass
                root.after(50, pump_queue)

            self._started.set()
            root.after(50, pump_queue)
            root.mainloop()
        except Exception as exc:
            logger.warning("Tk avatar renderer failed to start: %s", exc)
            self._started.set()
