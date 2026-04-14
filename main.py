import os
import sys
import logging
import threading as th
import time
from pathlib import Path
import queue as q
import asyncio
import subprocess
import inspect
import psutil
from typing import Any, Callable, Optional

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QApplication

from prompts import build_command_prompt, KWARGS_PROMPT
from app_logging import get_logger
from commands.commands_registry import build_command_pool, AppManager, DesktopManager

from src.gui.ipc_listener import IPCListener
from src.gui.settings_window import SettingsWindow
from src.gui.utils import setup_force_exit_fallback

from stt import LLMProcessor, CommandProcessor, run_voice_processing
from commands.commands_schema import Command, CommandEmptyArgs
from config import settings

from prompts import build_command_prompt, KWARGS_PROMPT 
from app_logging import get_logger
from commands.commands_registry import COMMAND_POOL
from avatar.src.avatar_service import AvatarService, build_avatar_service

logger: logging.Logger = get_logger(__name__)


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
        self.avatar_service: AvatarService = build_avatar_service()
        self.stop_event: Optional[th.Event] = None
        self.recorder_thread: Optional[th.Thread] = None
        self.loop_thread: Optional[th.Thread] = None
        self._init_tts()

    def _init_tts(self) -> None:
        """Lazy import of TTS to avoid unnecessary initialization effects for children processes"""
        from tts import TTS, CMD2VOICE
        self.tts = TTS()
        self._CMD2VOICE = CMD2VOICE

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
                self.avatar_service.on_command_rejected()
                continue

            command_fn = self.command_pool.get(cmd_name)
            if command_fn:
                self.avatar_service.on_command_started(cmd_name)
                try:
                    if inspect.iscoroutinefunction(command_fn):
                        asyncio.run(command_fn(**kwargs))
                    else:
                        command_fn(**kwargs)
                    self.avatar_service.on_command_succeeded(cmd_name)
                    logger.info("Work is done")
                except Exception:
                    self.avatar_service.on_command_failed(str(cmd_data))
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

        self.avatar_service.start()
        self.stop_event, self.recorder_thread = run_voice_processing(
            self.cfg.stt.model_dump(),
            self.queue,
            self.text_processor,
            status_callback=self.avatar_service.handle_stt_status,
        )
        self.stop_event, self.loop_thread = self._run_loop_in_thread(
            self.stop_event, self.queue
        )

    def stop(self) -> None:
        """Request shutdown and wait for worker threads to finish."""
        if not self.stop_event:
            return

        logger.info("App.stop(): signaling shutdown...")
        self.stop_event.set()

        self.recorder_thread.join()
        self.loop_thread.join()
        self.avatar_service.stop()


if __name__ == "__main__":
    app_manager = AppManager()
    desktop_manager = DesktopManager()
    command_pool = build_command_pool(app_manager, desktop_manager)

    # Initialize business logic
    app = App(settings, command_pool)
    app.start()

    # Start Qt GUI event loop
    qt_app = QApplication(sys.argv)

    # IPC listener for tray commands
    ipc = IPCListener()
    ipc.start()

    # Settings window
    config_path = Path("config.json").resolve()
    settings_win = SettingsWindow(config_path)

    # Connect IPC signals to UI
    ipc.open_settings_requested.connect(settings_win.show)
    ipc.open_settings_requested.connect(settings_win.raise_)

    def on_shutdown_requested():
        """Handle graceful shutdown request from SettingsWindow."""
        logger.info("Shutdown requested. Stopping background processes...")
        settings_win.hide()

        if ipc.notifier:
            ipc.notifier.setEnabled(False)

        def _shutdown_worker():
            try:
                app.stop(timeout=5.0)
                logger.info("Background processes stopped.")
            except Exception as e:
                logger.error(f"Shutdown error: {e}")
            finally:
                time.sleep(1)
                QMetaObject.invokeMethod(
                    qt_app, "quit", Qt.ConnectionType.QueuedConnection
                )
                setup_force_exit_fallback(delay_seconds=10.0)

        th.Thread(target=_shutdown_worker, daemon=True).start()

    settings_win.shutdown_requested.connect(on_shutdown_requested)
    settings_win.hide()  # Show only on tray signal

    logger.info("GUI started. Waiting for tray commands...")
    sys.exit(qt_app.exec())
