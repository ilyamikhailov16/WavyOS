import threading
import logging
import time
import socket
import ctypes
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as Item
import subprocess


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{self.COLORS['RESET']}"


logger = logging.getLogger("tray_app")
handler = logging.StreamHandler()
formatter = ColoredFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class AppState:
    def __init__(self):
        self.running_command = None
        self.icon = None


state = AppState()


def create_icon(color: str = "blue"):
    img = Image.new("RGB", (64, 64), color)
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="white")
    try:
        font = ImageFont.load_default()
        d.text((22, 15), "U", fill="black", font=font)
    except Exception:
        pass
    return img


def notify(title: str, message: str):
    try:
        if state.icon is not None and getattr(state.icon, "visible", False):
            state.icon.notify(message, title)
            logger.info(f"Уведомление: {title}")
        else:
            logger.info(f"[pre-tray] {title}: {message}")
    except Exception as e:
        logger.error(f"Notify failed: {e}")


def run_command(icon, name: str, command: str):
    if state.running_command:
        notify("Команда уже выполняется", f"{state.running_command} ещё выполняется")
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
                logger.info(f"{name} выполнена успешно")
            else:
                icon.icon = create_icon("red")
                error_text = result.stderr.strip() or "Неизвестная ошибка"
                notify(f"{name} - ошибка", error_text)
                logger.error(f"{name} ошибка: {error_text}")
        except Exception as e:
            icon.icon = create_icon("red")
            notify(f"{name} - ошибка", str(e))
            logger.error(f"{name} исключение: {e}")
        finally:
            time.sleep(2)
            icon.icon = create_icon("blue")
            icon.title = "UniversalApp"
            state.running_command = None

    threading.Thread(target=_worker, daemon=True).start()


def exit_app(icon, item):
    notify("Выход из трея", "Приложение успешно вышло из системного трея")
    logger.info("Приложение закрывается...")
    icon.stop()


def run_tray():
    icon = pystray.Icon(
        "UniversalApp",
        create_icon("blue"),
        "UniversalApp",
        menu=pystray.Menu(
            Item(
                "Команда 1",
                lambda i, item: run_command(i, "Команда 1", "echo Команда 1"),
            ),
            Item(
                "Команда 2",
                lambda i, item: run_command(i, "Команда 2", "echo Команда 2"),
            ),
            Item(
                "Тест ошибки",
                lambda i, item: run_command(
                    i, "Тест ошибки", "python -c \"raise RuntimeError('тест')\""
                ),
            ),
            Item("Выход", exit_app),
        ),
    )
    state.icon = icon

    def on_ready(icon):
        icon.visible = True
        notify(
            "Вход в трей", "Приложение успешно вошло в системный трей и готово к работе"
        )
        logger.info("Трей полностью готов")

    icon.run(setup=on_ready)


def fake_gui():
    logger.info("Основной поток приложения работает")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    logger.info("Запуск UniversalApp...")

    PORT = 65234
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", PORT))
        state._lock_socket = s
    except OSError:
        logger.warning("Приложение уже запущено!")
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Приложение уже работает в трее.\nНовый экземпляр закрыт.",
                "UniversalApp",
                0x40,
            )
        except Exception:
            pass
        exit(1)

    gui_thread = threading.Thread(target=fake_gui, daemon=True)
    gui_thread.start()

    run_tray()
