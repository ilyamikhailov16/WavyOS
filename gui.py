#!/usr/bin/env python3
"""
GUI process: PySide6 window + ZMQ clients for Core/Tray + Avatar UI.
"""
import sys
import logging
import threading as th
import time
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import zmq
from PySide6.QtCore import QMetaObject, Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication

from ipc.protocol import Message, MessageType, Command, SttStatusMessage
from app_logging import get_logger
from src.gui.settings_window import SettingsWindow
from src.gui.utils import setup_force_exit_fallback
from avatar.src.avatar_service import AvatarService, build_avatar_service

logger = get_logger("gui")

class SttStatusListener(QObject):
    """ZMQ SUB client: receives status strings and forwards to avatar_service."""
    status_received = Signal(str)

    def __init__(self, port: int = 5557, avatar_svc=None, parent=None):
        super().__init__(parent)
        self.ctx = zmq.Context()
        self.ctx.setsockopt(zmq.LINGER, 0)
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect(f"tcp://127.0.0.1:{port}")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.avatar_svc = avatar_svc  # <<< СОХРАНЯЕМ ССЫЛКУ НА АВАТАР

        self.timer = QTimer()
        self.timer.timeout.connect(self._check_messages)
        self.timer.start(50)
        logger.info(f"GUI: STT status SUB connected to port {port}")

    def _check_messages(self):
        socks = dict(self.poller.poll(0))
        if self.socket in socks and socks[self.socket] == zmq.POLLIN:
            try:
                raw = self.socket.recv_string(flags=zmq.NOBLOCK)
                data = json.loads(raw)

                # Если это статус команды → сразу вызываем методы аватара
                if data.get("type") == "cmd_status" and self.avatar_svc:
                    action = data.get("action")
                    name = data.get("name", "")
                    if action == "started":
                        self.avatar_svc.on_command_started(name)
                    elif action == "succeeded":
                        self.avatar_svc.on_command_succeeded(name)
                    elif action == "failed":
                        self.avatar_svc.on_command_failed(name)
                else:
                    # Обычный STT статус (слушаю/думаю)
                    status = data.get("status")
                    if status:
                        logger.info(f"GUI: Received STT status: '{status}'")
                        self.status_received.emit(status)
            except (json.JSONDecodeError, zmq.Again):
                pass
            except Exception as e:
                logger.error(f"GUI: Status receive error: {e}")

    def cleanup(self):
        self.timer.stop()
        if self.socket: self.socket.close()
        if self.ctx: self.ctx.term()


class TrayIPC(QObject):
    """ZMQ REP server for tray commands (port 5555). Strict recv→send cycle."""
    open_settings_requested = Signal()
    shutdown_requested = Signal()

    def __init__(self, port: int = 5555, parent=None):
        super().__init__(parent)
        self.ctx = zmq.Context()
        self.ctx.setsockopt(zmq.LINGER, 0)  # Не виснет при закрытии
        self.socket = self.ctx.socket(zmq.REP)
        self.socket.bind(f"tcp://127.0.0.1:{port}")

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.timer = QTimer()
        self.timer.timeout.connect(self._check_messages)
        self.timer.start(50)  # 50 мс ≈ 20 Гц опрос
        logger.info(f"TrayIPC server started on port {port}")

    def _check_messages(self):
        socks = dict(self.poller.poll(0))
        if self.socket in socks and socks[self.socket] == zmq.POLLIN:
            try:
                msg_data = self.socket.recv_json(flags=zmq.NOBLOCK)
                cmd = msg_data.get("command")
                msg_id = msg_data.get("msg_id")

                if cmd == "open_settings":
                    logger.info("Tray: OPEN_SETTINGS received")
                    self.open_settings_requested.emit()
                elif cmd == "shutdown":
                    logger.info("Tray: SHUTDOWN received")
                    self.shutdown_requested.emit()

                # ОБЯЗАТЕЛЬНО шлём ACK, чтобы не сломать REP-машина состояний
                self.socket.send_json({"ack": msg_id, "status": "ok"})
            except zmq.Again:
                pass
            except Exception as e:
                logger.error(f"IPC receive/send error: {e}")
                # Fallback ACK чтобы сокет не завис
                try:
                    self.socket.send_json({"ack": msg_data.get("msg_id"), "status": "error"})
                except: pass

    def cleanup(self):
        self.timer.stop()
        if self.socket: self.socket.close()
        if self.ctx: self.ctx.term()


def _do_shutdown(tray_ipc: TrayIPC, avatar_service: AvatarService, settings_win: SettingsWindow, qt_app: QApplication):
    """Graceful shutdown handler."""
    logger.info("GUI: Graceful shutdown initiated")
    settings_win.hide()
    avatar_service.stop()

    def _shutdown_worker():
        try:
            tray_ipc.cleanup()
            logger.info("GUI: IPC cleaned up")
        except Exception as e:
            logger.error(f"Shutdown IPC error: {e}")
        finally:
            QMetaObject.invokeMethod(qt_app, "quit", Qt.ConnectionType.QueuedConnection)
            setup_force_exit_fallback(delay_seconds=10.0)
    th.Thread(target=_shutdown_worker, daemon=True).start()


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)

    # 1. Создаём avatar_service ПЕРВЫМ
    avatar_service = build_avatar_service(
        on_avatar_window_closed=lambda: _do_shutdown(tray_ipc, avatar_service, settings_win, qt_app)
    )
    avatar_service.start()
    logger.info("GUI: Avatar service started")

    # 2. Создаём слушатель статусов
    stt_listener = SttStatusListener(port=5557, avatar_svc = avatar_service)

    # 3. Подключаем сигнал к методу аватара — строка передаётся как есть!
    stt_listener.status_received.connect(avatar_service.handle_stt_status)

    # 4. Остальная инициализация...
    tray_ipc = TrayIPC(port=5555)
    config_path = Path("config.json").resolve()
    settings_win = SettingsWindow(config_path)

    tray_ipc.open_settings_requested.connect(settings_win.show)
    tray_ipc.open_settings_requested.connect(settings_win.raise_)
    tray_ipc.shutdown_requested.connect(
        lambda: _do_shutdown(tray_ipc, avatar_service, settings_win, qt_app)
    )

    avatar_timer = QTimer()
    avatar_timer.timeout.connect(avatar_service.process_ui_events)
    avatar_timer.start(50)

    settings_win.hide()
    logger.info("GUI started. Waiting for commands...")

    try:
        exit_code = qt_app.exec()
    finally:
        avatar_timer.stop()
        stt_listener.cleanup()  # ← новая строка
        tray_ipc.cleanup()
        avatar_service.stop()

    sys.exit(exit_code)