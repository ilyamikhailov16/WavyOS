#!/usr/bin/env python3
"""
Tray process: pystray icon + ZMQ client to GUI.
"""

import threading
import time
import socket
import ctypes
import uuid

import zmq
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as Item
import subprocess
import sys

from wavy.app_logging import get_logger

logger = get_logger("tray")


class AppState:
    def __init__(self):
        self.running_command = None
        self.icon = None
        self.worker_thread = None
        self.lock_socket = None
        self.command_lock = threading.Lock()


state = AppState()


def create_icon(color: str = "blue"):
    img = Image.new("RGB", (64, 64), color)
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="white")
    try:
        font = ImageFont.load_default()
        d.text((22, 15), "U", fill="black", font=font)
    except:
        pass
    return img


def notify(title: str, message: str):
    try:
        if state.icon and getattr(state.icon, "visible", False):
            state.icon.notify(message, title)
            logger.info(f"Notify: {title}")
    except Exception as e:
        logger.error(f"Notify failed: {e}")


def run_command(icon, name: str, command: str):
    with state.command_lock:
        if state.running_command:
            notify(
                "Команда уже выполняется", f"{state.running_command} ещё выполняется"
            )
            return
        state.running_command = name

    icon.icon = create_icon("yellow")
    icon.title = f"UniversalApp — {name}"
    logger.info(f"{name} запущена")

    def _worker():
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                icon.icon = create_icon("green")
                notify(name, "Выполнено успешно")
            else:
                icon.icon = create_icon("red")
                notify(
                    f"{name} - ошибка", result.stderr.strip() or "Неизвестная ошибка"
                )
        except Exception as e:
            icon.icon = create_icon("red")
            notify(f"{name} - ошибка", str(e))
        finally:
            time.sleep(2)
            icon.icon = create_icon("blue")
            icon.title = "UniversalApp"
            with state.command_lock:
                state.running_command = None

    t = threading.Thread(target=_worker, daemon=False)
    state.worker_thread = t
    t.start()


def _send_gui_command(command: str, port: int = 5555, timeout_ms: int = 2000) -> bool:
    """Отправляет команду в GUI через ZMQ REQ/REP."""
    ctx = zmq.Context()
    ctx.setsockopt(zmq.LINGER, 0)
    socket = ctx.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    try:
        socket.connect(f"tcp://127.0.0.1:{port}")
        msg_id = str(uuid.uuid4())[:8]
        socket.send_json({"command": command, "msg_id": msg_id})
        resp = socket.recv_json()
        return resp.get("status") == "ok"
    except Exception as e:
        logger.warning(f"IPC to GUI failed: {e}")
        return False
    finally:
        socket.close()
        ctx.term()


def exit_app(icon, item):
    logger.info("Tray: Exit requested")
    if not _send_gui_command("shutdown"):
        logger.warning("Tray: GUI did not respond to SHUTDOWN — proceeding anyway")

    notify("Выход", "Завершение работы...")
    worker = state.worker_thread
    if worker and worker.is_alive():
        worker.join(timeout=5)
    if state.lock_socket:
        try:
            state.lock_socket.close()
        except:
            pass
    icon.stop()
    logger.info("Tray: Exited cleanly")


def run_tray():
    icon = pystray.Icon(
        "UniversalApp",
        create_icon("blue"),
        "UniversalApp",
        menu=pystray.Menu(
            Item("⚙ Настройки", lambda i, item: _send_gui_command("open_settings")),
            Item(
                "Выход",
                lambda i, item: (_send_gui_command("shutdown"), exit_app(i, item)),
            ),
        ),
    )
    state.icon = icon

    def on_ready(icon):
        icon.visible = True
        logger.info("Tray: Ready")

    icon.run(setup=on_ready)


if __name__ == "__main__":
    logger.info("Tray: Starting...")

    # Single-instance check via lock socket
    PORT = 65234
    try:
        import socket, ctypes

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.2", PORT))
        state.lock_socket = s
    except OSError:
        logger.warning("Tray: Application already running!")
        try:
            ctypes.windll.user32.MessageBoxW(
                0, "Приложение уже работает в трее.", "UniversalApp", 0x40
            )
        except:
            pass
        sys.exit(1)

    try:
        run_tray()
    finally:
        if state.lock_socket:
            try:
                state.lock_socket.close()
            except:
                pass
