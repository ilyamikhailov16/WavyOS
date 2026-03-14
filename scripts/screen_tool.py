import threading
import time
from pathlib import Path
import sys

import cv2
import numpy as np
import mss
import keyboard
import pyautogui

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings

SCREEN_TOOL_SETTINGS = settings.screen_tool
OUT_DIR = Path.cwd() / SCREEN_TOOL_SETTINGS.paths.records_dir_name
OUT_DIR.mkdir(exist_ok=True)

recording = False
record_thread = None


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def take_screenshot():
    img = pyautogui.screenshot()
    filename = Path.cwd() / f"{SCREEN_TOOL_SETTINGS.paths.screenshot_prefix}_{timestamp()}.png"
    img.save(filename)
    print(f"[✓] Скриншот сохранён: {filename}")


def record_screen():
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

        print(f"[●] Запись начата → {filename}")

        while recording:
            img = sct.grab(monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            out.write(frame)

        out.release()
        print("[■] Запись остановлена")


def start_recording():
    global recording, record_thread

    if recording:
        print("[!] Уже записывается")
        return

    recording = True
    record_thread = threading.Thread(target=record_screen)
    record_thread.start()


def stop_recording():
    global recording
    if not recording:
        print("[!] Запись не запущена")
        return
    recording = False


def toggle_recording():
    if recording:
        stop_recording()
    else:
        start_recording()


def hotkeys():
    print("=== РЕЖИМ ГОРЯЧИХ КЛАВИШ ===")
    print("F9  → старт / стоп записи")
    print("F12 → скриншот")
    print("ESC → выход")
    print("----------------------------")

    keyboard.add_hotkey(SCREEN_TOOL_SETTINGS.hotkeys.toggle_recording, toggle_recording)
    keyboard.add_hotkey(SCREEN_TOOL_SETTINGS.hotkeys.screenshot, take_screenshot)

    keyboard.wait(SCREEN_TOOL_SETTINGS.hotkeys.exit)

    if recording:
        stop_recording()

    print("Выход...")


if __name__ == "__main__":
    hotkeys()

