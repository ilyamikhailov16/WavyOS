import socket
import logging
from PySide6.QtCore import QObject, Signal, QSocketNotifier

logger = logging.getLogger(__name__)
IPC_PORT = 65234

class IPCListener(QObject):
    open_settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_socket = None
        self.notifier = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setblocking(False)
        self.server_socket.bind(("127.0.0.1", IPC_PORT))
        self.server_socket.listen(5)

        self.notifier = QSocketNotifier(
            self.server_socket.fileno(), QSocketNotifier.Type.Read, self
        )
        self.notifier.activated.connect(self._accept_connection)
        logger.info(f"IPC Listener запущен на порту {IPC_PORT}")

    def _accept_connection(self):
        """Accepts connection, reads command, closes client socket."""
        try:
            client, _ = self.server_socket.accept()
            client.setblocking(False)
            try:
                data = client.recv(1024).decode("utf-8", errors="ignore").strip()
                if data == "OPEN_SETTINGS":
                    logger.info("Получена команда открытия настроек от трей-процесса")
                    self.open_settings_requested.emit()
            except BlockingIOError:
                pass
            except (ConnectionResetError, OSError) as e:
                if getattr(e, "winerror", None) != 10035:
                    logger.error(f"Ошибка приёма IPC сообщения: {e}")
            finally:
                client.close()
        except BlockingIOError:
            pass
        except OSError as e:
            if getattr(e, "winerror", None) != 10035:
                logger.error(f"Ошибка принятия IPC соединения: {e}")

    def stop(self):
        if self.notifier:
            self.notifier.setEnabled(False)
        if self.server_socket:
            self.server_socket.close()