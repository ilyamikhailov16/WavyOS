
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import mss
import keyboard
import pyautogui

OUT_DIR = Path.cwd() / "screen_records"
OUT_DIR.mkdir(exist_ok=True)

recording = False
record_thread = None


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def take_screenshot():
    img = pyautogui.screenshot()
    filename = Path.cwd() / f"screenshot_{timestamp()}.png"
    img.save(filename)
    print(f"[✓] Скриншот сохранён: {filename}")


def record_screen():
    global recording

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        width = monitor["width"]
        height = monitor["height"]

        filename = OUT_DIR / f"record_{timestamp()}.avi"

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(str(filename), fourcc, 20.0, (width, height))

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

    keyboard.add_hotkey("F9", toggle_recording)
    keyboard.add_hotkey("F12", take_screenshot)

    keyboard.wait("esc")

    if recording:
        stop_recording()

    print("Выход...")


if __name__ == "__main__":
    hotkeys()

