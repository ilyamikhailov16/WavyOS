# Отвечает за приём команд от процесса pystray.

import socket
import logging
from PySide6.QtCore import QObject, Signal, QSocketNotifier

logger = logging.getLogger(__name__)

# Порт уже используется в tray.py для проверки "одного экземпляра"
IPC_PORT = 65234


class IPCListener(QObject):
    # Сигнал, который будет ловить GUI-окно
    open_settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_socket = None
        self.notifier = None

    def start(self):
        """Запускает прослушку порта в главном потоке."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", IPC_PORT))
        self.server_socket.listen(5)

        # QSocketNotifier вызывает self._accept_connection при готовности сокета
        # SocketType.ReadNotify = готовность к чтению/приёму соединения
        self.notifier = QSocketNotifier(
            self.server_socket.fileno(), QSocketNotifier.Type.Read, self
        )
        self.notifier.activated.connect(self._accept_connection)
        logger.info(f"IPC Listener запущен на порту {IPC_PORT}")

    def _accept_connection(self):
        """Принимает входящее соединение от pystray."""
        client, addr = self.server_socket.accept()
        try:
            data = client.recv(1024).decode().strip()
            if data == "OPEN_SETTINGS":
                logger.info("Получена команда открытия настроек от трей-процесса")
                self.open_settings_requested.emit()
        except Exception as e:
            logger.error(f"Ошибка приёма IPC сообщения: {e}")
        finally:
            client.close()

    def stop(self):
        if self.notifier:
            self.notifier.setEnabled(False)
        if self.server_socket:
            self.server_socket.close()
