import threading as th
import time
import os
import logging

logger = logging.getLogger(__name__)


def setup_force_exit_fallback(delay_seconds: float = 10.0):
    """
    Запускает daemon-поток, который принудительно завершит процесс,
    если основной выход не сработал за `delay_seconds`.
    Использовать только как последний рубеж.
    """

    def _force_exit():
        time.sleep(delay_seconds)
        logger.warning(
            f"Таймаут {delay_seconds}с истёк. Принудительное завершение процесса."
        )
        os._exit(0)  # Жёсткий выход, но только если всё остальное не сработало

    th.Thread(target=_force_exit, daemon=True).start()
