import threading
import time
from pathlib import Path
import platform
import logging

import cv2
import mss
import numpy as np
import pyautogui

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except Exception:
    KEYBOARD_AVAILABLE = False


class ScreenToolPaths:
    def __init__(self):
        self.base_user_dir: Path = Path.home() / "ScreenTool"
        self.screenshots_dir_name: str = "screenshots"
        self.records_dir_name: str = "records"
        self.screenshot_prefix: str = "screenshot"
        self.record_prefix: str = "record"
        self.record_extension: str = "mp4"


class ScreenToolHotkeys:
    def __init__(self):
        self.toggle_recording: str = "ctrl+shift+r"
        self.screenshot: str = "ctrl+shift+s"
        self.exit: str = "esc"


class ScreenToolSettings:
    def __init__(self):
        self.paths = ScreenToolPaths()
        self.hotkeys = ScreenToolHotkeys()
        self.fps: int = 20
        self.video_codec: str = "mp4v"


settings = ScreenToolSettings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("screen_tool")

BASE_DIR = settings.paths.base_user_dir
SCREENSHOTS_DIR = BASE_DIR / settings.paths.screenshots_dir_name
RECORDS_DIR = BASE_DIR / settings.paths.records_dir_name

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
RECORDS_DIR.mkdir(parents=True, exist_ok=True)

recording = False
record_thread = None


def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def take_screenshot() -> None:
    img = pyautogui.screenshot()
    filename = SCREENSHOTS_DIR / f"{settings.paths.screenshot_prefix}_{timestamp()}.png"
    img.save(filename)
    logger.info("Screenshot saved: %s", filename)


def record_screen() -> None:
    global recording

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        width = monitor["width"]
        height = monitor["height"]

        filename = RECORDS_DIR / f"{settings.paths.record_prefix}_{timestamp()}.{settings.paths.record_extension}"

        fourcc = cv2.VideoWriter_fourcc(*settings.video_codec)
        out = cv2.VideoWriter(str(filename), fourcc, settings.fps, (width, height))

        logger.info("Recording started: %s", filename)

        while recording:
            img = sct.grab(monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            out.write(frame)

        out.release()
        logger.info("Recording stopped.")


def start_recording() -> None:
    global recording, record_thread

    if recording:
        return

    recording = True
    record_thread = threading.Thread(target=record_screen, daemon=True)
    record_thread.start()


def stop_recording() -> None:
    global recording

    if not recording:
        return

    recording = False


def toggle_recording() -> None:
    if recording:
        stop_recording()
    else:
        start_recording()


def hotkeys() -> None:
    if not KEYBOARD_AVAILABLE:
        return

    keyboard.add_hotkey(settings.hotkeys.toggle_recording, toggle_recording)
    keyboard.add_hotkey(settings.hotkeys.screenshot, take_screenshot)

    keyboard.wait(settings.hotkeys.exit)

    if recording:
        stop_recording()


def cli_mode():
    while True:
        cmd = input("r=rec, s=shot, q=quit > ").strip().lower()

        if cmd == "r":
            toggle_recording()
        elif cmd == "s":
            take_screenshot()
        elif cmd == "q":
            if recording:
                stop_recording()
            break


if __name__ == "__main__":
    if KEYBOARD_AVAILABLE and platform.system() != "Emscripten":
        hotkeys()
    else:
        cli_mode()