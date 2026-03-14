import threading
import time
from pathlib import Path

import cv2
import keyboard
import mss
import numpy as np
import pyautogui

from app_logging import get_logger
from bootstrap import settings


SCREEN_TOOL_SETTINGS = settings.screen_tool
OUT_DIR = Path.cwd() / SCREEN_TOOL_SETTINGS.paths.records_dir_name
OUT_DIR.mkdir(exist_ok=True)

logger = get_logger(__name__)
recording = False
record_thread = None


def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def take_screenshot() -> None:
    img = pyautogui.screenshot()
    filename = Path.cwd() / f"{SCREEN_TOOL_SETTINGS.paths.screenshot_prefix}_{timestamp()}.png"
    img.save(filename)
    logger.info("Screenshot saved: %s", filename)


def record_screen() -> None:
    global recording

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        width = monitor["width"]
        height = monitor["height"]
        filename = (
            OUT_DIR
            / f"{SCREEN_TOOL_SETTINGS.paths.record_prefix}_{timestamp()}.{SCREEN_TOOL_SETTINGS.paths.record_extension}"
        )
        fourcc = cv2.VideoWriter_fourcc(*SCREEN_TOOL_SETTINGS.video_codec)
        out = cv2.VideoWriter(str(filename), fourcc, SCREEN_TOOL_SETTINGS.fps, (width, height))

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
        logger.warning("Recording is already in progress.")
        return

    recording = True
    record_thread = threading.Thread(target=record_screen)
    record_thread.start()


def stop_recording() -> None:
    global recording
    if not recording:
        logger.warning("Recording is not running.")
        return
    recording = False


def toggle_recording() -> None:
    if recording:
        stop_recording()
    else:
        start_recording()


def hotkeys() -> None:
    logger.info("Hotkey mode started.")
    keyboard.add_hotkey(SCREEN_TOOL_SETTINGS.hotkeys.toggle_recording, toggle_recording)
    keyboard.add_hotkey(SCREEN_TOOL_SETTINGS.hotkeys.screenshot, take_screenshot)
    keyboard.wait(SCREEN_TOOL_SETTINGS.hotkeys.exit)

    if recording:
        stop_recording()

    logger.info("Exiting hotkey mode.")


if __name__ == "__main__":
    hotkeys()
