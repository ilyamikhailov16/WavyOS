import sys
import logging
import threading as th
from pathlib import Path
import queue as q
import asyncio
import inspect

from prompts import build_command_prompt, KWARGS_PROMPT
from app_logging import get_logger
from commands.commands_registry import COMMAND_POOL

from typing import Any, Callable, Optional
from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QApplication

from stt import LLMProcessor, CommandProcessor, run_voice_processing
from commands.commands_schema import Command, CommandEmptyArgs
from config import settings

from src.gui.ipc_listener import IPCListener
from src.gui.settings_window import SettingsWindow
from src.gui.utils import setup_force_exit_fallback

logger: logging.Logger = get_logger(__name__)
# logging.getLogger().setLevel(logging.ERROR)


class App:
    """Main application runner for speech-to-command processing."""

    def __init__(self, cfg: Any, command_pool: dict) -> None:
        """
        Create an application instance.

        Args:
            cfg: Application configuration object (expects `.llm` and `.stt` sections).
        """

        self.cfg: Any = cfg
        self.command_pool: dict = command_pool
        self.queue: q.Queue[Command] = q.Queue()
        self.text_processor: Callable[[str], str | None] = self._build_text_processor()
        self.stop_event: Optional[th.Event] = None
        self.recorder_thread: Optional[th.Thread] = None
        self.loop_thread: Optional[th.Thread] = None

    def _build_text_processor(self) -> Callable[[str], str | None]:
        """Build a text post-processor that maps raw STT text to a command token."""
        if self.cfg.llm.use_for_stt:
            return CommandProcessor(
                command_name_processor = LLMProcessor(
                    base_url=self.cfg.llm.base_url,
                    api_key=self.cfg.llm.token,
                    model_path=self.cfg.llm.model,
                    system_prompt=build_command_prompt(self.command_pool),
                ),
                kwargs_processor = LLMProcessor(
                    base_url=self.cfg.llm.base_url,
                    api_key=self.cfg.llm.token,
                    model_path=self.cfg.llm.model,
                    system_prompt=KWARGS_PROMPT,
                ),
            )
        return lambda text: text

    def _run_loop(self, stop_event: th.Event, queue: q.Queue[str]) -> None:
        """Consume recognized commands from a queue and execute matching handlers."""
        while not stop_event.is_set():
            try:
                command = queue.get(timeout=0.5)
            except q.Empty:
                continue

            cmd_data = command.command
            logger.info("Recognised command: %s", cmd_data)

            cmd_name = cmd_data.command_name
            kwargs = (
                {}
                if isinstance(cmd_data.kwargs, CommandEmptyArgs)
                else cmd_data.kwargs.model_dump()
            )

            if cmd_name == "#":
                continue

            command_fn = self.command_pool.get(cmd_name)
            if command_fn:
                try:
                    if inspect.iscoroutinefunction(command_fn):
                        asyncio.run(command_fn(**kwargs))
                    else:
                        command_fn(**kwargs)
                    logger.info("Work is done")
                except Exception:
                    logger.exception("Exception caught while executing command")

    def _run_loop_in_thread(
        self, stop_event: th.Event, queue: q.Queue[str]
    ) -> tuple[th.Event, th.Thread]:
        """Start the command execution loop in a dedicated thread."""

        loop_thread = th.Thread(target=self._run_loop, args=(stop_event, queue))
        loop_thread.start()
        return stop_event, loop_thread


    def start(self) -> None:
        """Start voice processing and the command execution loop."""

        self.stop_event, self.recorder_thread = run_voice_processing(
            self.cfg.stt.model_dump(), self.queue, self.text_processor
        )
        self.stop_event, self.loop_thread = self._run_loop_in_thread(
            self.stop_event, self.queue
        )

    def stop(self, timeout: float = 3.0) -> None:
        """Request shutdown and wait for worker threads to finish."""
        if not self.stop_event:
            return

        logger.info("App.stop(): сигналим о завершении...")
        self.stop_event.set()

        # 1. Пытаемся корректно завершить потоки
        threads_to_join = [
            ("recorder_thread", self.recorder_thread),
            ("loop_thread", self.loop_thread),
        ]

        for name, thread in threads_to_join:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)
                if thread.is_alive():
                    logger.warning(f"{name} не завершился за {timeout}с, продолжаем...")

        # 2. Агрессивная очистка дочерних процессов (RealtimeSTT + PyAudio)
        try:
            import psutil
            current = psutil.Process()
            children = current.children(recursive=True)

            if children:
                logger.info(f"Найдено {len(children)} дочерних процессов, завершаем...")

                # Сначала мягкий сигнал
                for child in children:
                    try:
                        logger.debug(f"  → SIGTERM: {child.pid} ({child.name()})")
                        child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Ждём 1.5с на корректное завершение
                gone, alive = psutil.wait_procs(children, timeout=1.5)

                # Если кто-то остался — убиваем жёстко
                for proc in alive:
                    try:
                        logger.warning(f"  → SIGKILL: {proc.pid} ({proc.name()})")
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                logger.info("Очистка дочерних процессов завершена")

        except ImportError:
            logger.warning("psutil не установлен, пропускаем очистку процессов")
        except Exception as e:
            logger.error(f"Ошибка при очистке процессов: {e}")

        logger.info("App.stop(): завершено")

if __name__ == "__main__":
    # 1. Инициализация бизнес-логики
    app = App(settings, COMMAND_POOL)
    app.start()  # Запускает recorder_thread и loop_thread в фоне

    # 2. Запуск GUI Event Loop (главный поток теперь здесь)
    qt_app = QApplication(sys.argv)

    # IPC Listener для приёма команд от pystray
    ipc = IPCListener()
    ipc.start()

    # Окно настроек
    config_path = Path("config.json").resolve()
    settings_win = SettingsWindow(config_path)

    # Связь: сокет получил команду -> показать окно
    ipc.open_settings_requested.connect(settings_win.show)
    ipc.open_settings_requested.connect(settings_win.raise_)

    #  Обработчик запроса на завершение (вызывается из SettingsWindow)
    def on_shutdown_requested():
        logger.info("Получен запрос на завершение. Остановка фоновых процессов...")
        settings_win.close()

        # Отключаем IPC-слушатель в главном потоке (безопасно для Qt-объектов)
        if ipc.notifier:
            ipc.notifier.setEnabled(False)

        def _shutdown_worker():
            try:
                #  Используем уже готовую логику остановки из App
                app.stop(timeout=3.0)
                logger.info("Фоновые процессы корректно завершены.")
            except Exception as e:
                logger.error(f"Ошибка при завершении: {e}")
            finally:
                # Жесткий выход через 10 секунд
                setup_force_exit_fallback(delay_seconds=10.0)
                #  Корректный выход из Qt Event Loop (потокобезопасно)
                QMetaObject.invokeMethod(
                    qt_app, "quit",
                    Qt.ConnectionType.QueuedConnection
                )

        # Запускаем остановку в отдельном потоке, чтобы не блокировать GUI
        th.Thread(target=_shutdown_worker, daemon=True).start()

    settings_win.shutdown_requested.connect(on_shutdown_requested)

    # Скрываем окно при старте, оно появится только по сигналу из трея
    settings_win.hide()

    logger.info("GUI запущен. Ожидание команд от системного трея...")
    sys.exit(qt_app.exec())