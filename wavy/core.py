#!/usr/bin/env python3
"""
Core process: STT, TTS, AppManager, command execution.
Communicates with GUI via ZMQ REP on port 5556.
NO Qt/PySide6 imports allowed here.
"""

import sys
import json
import threading as th
import time
import asyncio
import queue as q
from pathlib import Path
from typing import Optional
import string

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from ipc.protocol import Message, MessageType, Command, SttStatusMessage
from ipc.zmq_utils import (
    create_context,
    bind_rep_socket,
    send_message,
    recv_message,
    poll_socket,
)

from wavy.app_logging import get_logger
from wavy.commands.commands_registry import build_command_pool, AppManager, DesktopManager
from wavy.stt import run_voice_processing, LLMProcessor, CommandProcessor
from wavy.prompts import build_command_prompt, KWARGS_PROMPT
from wavy.config import settings
from wavy.commands.commands_schema import (
    CmdLaunchApp,
    CmdOpenBrowser,
    CmdCreateFile,
    CmdCreateFolder,
    CmdDelete,
    CmdRunScript,
    Command as Cmd,
    CommandEmptyArgs,
    CommandApp,
    CommandOpenBrowser,
    CommandCreateFile,
    CommandCreateFolder,
    CommandDelete,
    CommandRename,
    CommandRunScript,
    # === Commands without args ===
    CmdEmptyRecycleBin,
    CmdScreenshot,
    CmdShutdown,
    CmdToggleWifi,
    CmdToggleNotifications,
    CmdToggleAirplaneMode,
    CmdToggleBluetooth,
    CmdToggleMute,
    CmdEnableEnergySaverMode,
    CmdDisableEnergySaverMode,
    CmdStartRecording,
    CmdStopRecording,
    CmdUnknown,
)
from commands.commands_keys import (
    CMD_EMPTY_RECYCLE_BIN,
    CMD_SCREENSHOT,
    CMD_SHUTDOWN,
    CMD_WIFI,
    CMD_NOTIFICATIONS,
    CMD_AIRPLANE,
    CMD_BLUETOOTH,
    CMD_SOUND,
    CMD_ENERGY_SAVER_ON,
    CMD_ENERGY_SAVER_OFF,
    CMD_RECORD_ON,
    CMD_RECORD_OFF,
    CMD_LAUNCH_APP,
    CMD_CLOSE_APP,
    CMD_UNINSTALL_APP,
    CMD_CREATE_FILE,
    CMD_CREATE_FOLDER,
    CMD_DELETE,
    CMD_RENAME,
    CMD_RUN_SCRIPT,
    CMD_OPEN_SITE,
)
from ipc.protocol import SttStatusMessage

logger = get_logger("core")


class CoreApp:
    """Core application logic, isolated from GUI."""

    def __init__(self, cfg, command_pool: dict):
        self.cfg = cfg
        self.command_pool = command_pool
        self.queue: q.Queue = q.Queue()
        self.text_processor = self._build_text_processor()
        self.stop_event: Optional[th.Event] = None
        self.recorder_thread: Optional[th.Thread] = None
        self.loop_thread: Optional[th.Thread] = None
        self._stopped = False
        self._init_tts()
        self._init_stt_pub()

    def _init_tts(self):
        from tts import TTS, CMD2VOICE

        self.tts = TTS()
        self._CMD2VOICE = CMD2VOICE

    def _init_stt_pub(self):
        """Initialize ZMQ PUB socket for broadcasting STT status to GUI."""
        import zmq

        self.stt_pub_ctx = zmq.Context()
        self.stt_pub_ctx.setsockopt(zmq.LINGER, 0)
        self.stt_pub = self.stt_pub_ctx.socket(zmq.PUB)
        self.stt_pub.bind("tcp://127.0.0.1:5557")
        logger.info("Core: STT status PUB bound to port 5557")

    def _notify_gui_cmd_status(self, action: str, cmd_name: str = ""):
        """Отправляет статус выполнения команды в GUI через PUB-сокет."""
        try:
            msg = json.dumps({"type": "cmd_status", "action": action, "name": cmd_name})
            self.stt_pub.send_string(msg)
        except Exception as e:
            logger.warning(f"Core: Failed to send cmd status: {e}")

    def _build_text_processor(self):
        """Build processor with keyword-based routing when LLM is disabled."""

        # === Маппинг: ключевые слова → (класс, константа имени) ===
        # Команды БЕЗ аргументов
        NO_ARGS_COMMANDS = {
            "очисти корзину": (CmdEmptyRecycleBin, CMD_EMPTY_RECYCLE_BIN),
            "сделай скриншот": (CmdScreenshot, CMD_SCREENSHOT),
            "выключи компьютер": (CmdShutdown, CMD_SHUTDOWN),
            "wi-fi": (CmdToggleWifi, CMD_WIFI),
            "уведомления": (CmdToggleNotifications, CMD_NOTIFICATIONS),
            "режим полёта": (CmdToggleAirplaneMode, CMD_AIRPLANE),
            "bluetooth": (CmdToggleBluetooth, CMD_BLUETOOTH),
            "звук": (CmdToggleMute, CMD_SOUND),
            "включи энергосбережение": (CmdEnableEnergySaverMode, CMD_ENERGY_SAVER_ON),
            "выключи энергосбережение": (
                CmdDisableEnergySaverMode,
                CMD_ENERGY_SAVER_OFF,
            ),
            "включи запись экрана": (CmdStartRecording, CMD_RECORD_ON),
            "выключи запись экрана": (CmdStopRecording, CMD_RECORD_OFF),
        }

        # Команды С аргументами (обрабатываются отдельно)
        ARGS_COMMANDS_KEYWORDS = {
            "открой приложение": CMD_LAUNCH_APP,
            "закрой приложение": CMD_CLOSE_APP,
            "удали приложение": CMD_UNINSTALL_APP,
            "создай файл": CMD_CREATE_FILE,
            "создай папку": CMD_CREATE_FOLDER,
            "удали": CMD_DELETE,
            "переименуй": CMD_RENAME,
            "запусти скрипт": CMD_RUN_SCRIPT,
            "открой сайт": CMD_OPEN_SITE,
        }

        def _status_wrapper(status: str):
            msg = SttStatusMessage(msg_id=f"stt_{time.time()}", status=status)
            try:
                self.stt_pub.send_string(msg.to_json())
            except Exception as e:
                logger.warning(f"Core: Failed to broadcast STT status: {e}")

        # Если LLM включён и есть токен — используем CommandProcessor
        if self.cfg.llm.use_for_stt and self.cfg.llm.token.strip():
            return CommandProcessor(
                command_name_processor=LLMProcessor(
                    base_url=self.cfg.llm.base_url,
                    api_key=self.cfg.llm.token,
                    model_path=self.cfg.llm.model,
                    system_prompt=build_command_prompt(self.command_pool),
                ),
                kwargs_processor=LLMProcessor(
                    base_url=self.cfg.llm.base_url,
                    api_key=self.cfg.llm.token,
                    model_path=self.cfg.llm.model,
                    system_prompt=KWARGS_PROMPT,
                ),
            )

        # Fallback: роутер по ключевым словам
        def _keyword_router(text: str):
            clean = text.strip().rstrip(string.punctuation + ".,!?;:").lower()
            if not clean:
                return None

            # 1. Проверяем команды БЕЗ аргументов (точное совпадение или вхождение)
            for keyword, (cmd_cls, cmd_name) in NO_ARGS_COMMANDS.items():
                if keyword in clean:
                    _status_wrapper("transcription_started")
                    wrapper = cmd_cls(command_name=cmd_name, kwargs=CommandEmptyArgs())
                    return Cmd(command=wrapper)

            # 2. Проверяем команды С аргументами
            for keyword, cmd_name in ARGS_COMMANDS_KEYWORDS.items():
                if keyword in clean:
                    _status_wrapper("transcription_started")
                    # Извлекаем аргумент: всё, что после ключевого слова
                    arg_text = clean.replace(keyword, "").strip()

                    if cmd_name == CMD_LAUNCH_APP:
                        kwargs_obj = CommandApp(
                            app_name=arg_text if arg_text else "unknown"
                        )
                        wrapper = CmdLaunchApp(command_name=cmd_name, kwargs=kwargs_obj)
                    elif cmd_name == CMD_OPEN_SITE:
                        kwargs_obj = CommandOpenBrowser(
                            website_name=arg_text if arg_text else "example.com"
                        )
                        wrapper = CmdOpenBrowser(
                            command_name=cmd_name, kwargs=kwargs_obj
                        )
                    elif cmd_name == CMD_CREATE_FILE:
                        kwargs_obj = CommandCreateFile(
                            filename=arg_text if arg_text else "untitled.txt"
                        )
                        wrapper = CmdCreateFile(
                            command_name=cmd_name, kwargs=kwargs_obj
                        )
                    elif cmd_name == CMD_CREATE_FOLDER:
                        kwargs_obj = CommandCreateFolder(
                            name=arg_text if arg_text else "new_folder"
                        )
                        wrapper = CmdCreateFolder(
                            command_name=cmd_name, kwargs=kwargs_obj
                        )
                    elif cmd_name in (CMD_DELETE, CMD_RENAME):
                        kwargs_obj = CommandDelete(
                            name=arg_text if arg_text else "unknown"
                        )
                        wrapper = CmdDelete(command_name=cmd_name, kwargs=kwargs_obj)
                    elif cmd_name == CMD_RUN_SCRIPT:
                        kwargs_obj = CommandRunScript(
                            script_name=arg_text if arg_text else "script.py"
                        )
                        wrapper = CmdRunScript(command_name=cmd_name, kwargs=kwargs_obj)
                    else:
                        # Fallback для остальных: пустые аргументы
                        wrapper = type(
                            "FallbackCmd",
                            (),
                            {"command_name": cmd_name, "kwargs": CommandEmptyArgs()},
                        )()
                        # Это упрощение — в реальном коде нужно импортировать правильный класс
                        # Но для большинства команд с аргументами выше уже есть обработка
                        continue

                    return Cmd(command=wrapper)

            # 3. Если ничего не совпало — дефолт: запуск приложения
            _status_wrapper("listening_started")
            kwargs_obj = CommandApp(app_name=clean)
            wrapper_obj = CmdLaunchApp(command_name=CMD_LAUNCH_APP, kwargs=kwargs_obj)
            return Cmd(command=wrapper_obj)

        logger.warning("Core: LLM disabled. Using keyword-based router.")
        return _keyword_router

    def _run_loop(self, stop_event: th.Event, queue: q.Queue):
        """Command execution loop — runs in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while not stop_event.is_set():
                try:
                    command = queue.get(timeout=0.5)
                except q.Empty:
                    continue
                except BrokenPipeError:
                    logger.warning("Core: Queue pipe closed, exiting loop")
                    break

                cmd_data = command.command
                logger.info(f"Recognised command: {cmd_data}")

                cmd_name = cmd_data.command_name
                kwargs = (
                    {}
                    if isinstance(cmd_data.kwargs, CommandEmptyArgs)
                    else cmd_data.kwargs.model_dump()
                )

                if cmd_name == "#":
                    continue

                self._notify_gui_cmd_status("started", cmd_name)

                command_fn = self.command_pool.get(cmd_name)
                if command_fn:
                    try:
                        result = command_fn(**kwargs)
                        if asyncio.iscoroutine(result):
                            loop.run_until_complete(result)

                        self.tts.stop()
                        text = self._CMD2VOICE[cmd_name].format(**kwargs)
                        self.tts.play(text)
                        self._notify_gui_cmd_status("succeeded", cmd_name)
                        logger.info("Work is done")
                        try:
                            reset_msg = json.dumps({"status": "listening_started"})
                            self.stt_pub.send_string(reset_msg)
                            logger.debug("Core: Reset avatar to listening mode")
                        except Exception as e:
                            logger.warning(f"Core: Failed to reset avatar: {e}")
                    except Exception:
                        self._notify_gui_cmd_status("failed", cmd_name)
                        logger.exception("Exception caught while executing command")
                        # Сброс аватара даже при ошибке
                        try:
                            reset_msg = json.dumps({"status": "listening_started"})
                            self.stt_pub.send_string(reset_msg)
                        except:
                            pass
        finally:
            loop.close()

    def start(self) -> None:
        logger.info("Core: Initializing STT...")

        def _stt_status_callback(status: str):
            """Отправляет статус STT в GUI через PUB-сокет."""
            try:
                # Простой JSON для STT статусов
                msg = json.dumps({"status": status})
                self.stt_pub.send_string(msg)
            except Exception as e:
                logger.warning(f"Core: Failed to send STT status: {e}")

        try:
            self.stop_event, self.recorder_thread = run_voice_processing(
                self.cfg.stt.model_dump(),
                self.queue,
                self.text_processor,
                status_callback=_stt_status_callback,  # ← настоящий колбэк вместо dummy_cb!
            )
            logger.info("Core: STT started successfully")
        except Exception as e:
            logger.critical(f"Core: STT initialization FAILED: {e}", exc_info=True)
            self.stop_event = th.Event()
            self.stop_event.set()

        logger.info("Core: Starting command loop thread...")
        self.loop_thread = th.Thread(
            target=self._run_loop,
            args=(self.stop_event, self.queue),
            daemon=True,
        )
        self.loop_thread.start()
        logger.info("Core started")

    def stop(self, timeout: float = 3.0):
        """Graceful shutdown."""
        if self._stopped:
            return
        self._stopped = True

        if self.stop_event:
            logger.info("Core.stop(): signaling shutdown...")
            self.stop_event.set()

            for name, thread in [
                ("recorder", self.recorder_thread),
                ("loop", self.loop_thread),
            ]:
                if thread and thread.is_alive():
                    thread.join(timeout=timeout)

        self.tts.stop()
        self._cleanup_child_processes()
        logger.info("Core stopped")


def handle_core_request(
    msg: Message, core: CoreApp, app_manager: AppManager
) -> Message:
    """Process incoming command from GUI."""
    try:
        if msg.command == Command.LAUNCH_APP:
            name = msg.payload.get("name")
            result = app_manager.launch_app(name)
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.RESPONSE,
                command=msg.command,
                payload={"status": result.status.value, "message": result.message},
            )

        elif msg.command == Command.CLOSE_APP:
            name = msg.payload.get("name")
            result = app_manager.close_app(name)
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.RESPONSE,
                command=msg.command,
                payload={"status": result.status.value, "message": result.message},
            )

        elif msg.command == Command.UNINSTALL_APP:
            name = msg.payload.get("name")
            result = app_manager.uninstall_app(name)
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.RESPONSE,
                command=msg.command,
                payload={"status": result.status.value, "message": result.message},
            )

        elif msg.command == Command.LIST_RUNNING_APPS:
            result = app_manager.list_running_apps()
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.RESPONSE,
                command=msg.command,
                payload={"processes": result.data.get("processes", [])},
            )

        elif msg.command == Command.IS_APP_RUNNING:
            name = msg.payload.get("name")
            result = app_manager.is_app_running(name)
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.RESPONSE,
                command=msg.command,
                payload={"running": result.data.get("running", False)},
            )

        else:
            return Message(
                msg_id=msg.msg_id,
                msg_type=MessageType.ERROR,
                command=msg.command,
                error=f"Unknown command: {msg.command}",
            )

    except Exception as e:
        logger.exception(f"Error handling {msg.command}")
        return Message(
            msg_id=msg.msg_id,
            msg_type=MessageType.ERROR,
            command=msg.command,
            error=str(e),
        )


def run_core_server(port: int = 5556):
    """Main entry point for core process."""
    logger.info(f"Starting Core server on port {port}")

    # Initialize components
    app_manager = AppManager()
    desktop_manager = DesktopManager()
    command_pool = build_command_pool(app_manager, desktop_manager)
    core = CoreApp(settings, command_pool)
    core.start()

    # ZMQ server
    ctx = create_context()
    socket = bind_rep_socket(ctx, port, "core")

    try:
        while True:
            if poll_socket(socket, timeout_ms=100):
                msg = recv_message(socket, "core")
                if msg and msg.msg_type == MessageType.REQUEST:
                    response = handle_core_request(msg, core, app_manager)
                    send_message(socket, response, "core")

    except KeyboardInterrupt:
        logger.info("Core: Interrupt received")
    except Exception as e:
        logger.error(f"Core: Fatal error: {e}", exc_info=True)
    finally:
        # 1. Останавливаем потоки
        if core.stop_event:
            core.stop_event.set()
        if core.recorder_thread and core.recorder_thread.is_alive():
            core.recorder_thread.join(timeout=2.0)
        if core.loop_thread and core.loop_thread.is_alive():
            core.loop_thread.join(timeout=2.0)

        # 2. Останавливаем CoreApp (TTS, cleanup)
        core.stop(timeout=1.0)

        # 3. Убиваем "зомби"-детей (RealtimeSTT/faster_whisper часто оставляют их)
        try:
            import psutil, os

            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except:
                    pass
        except:
            pass

        # 4. Закрываем сеть
        logger.info("Core: Closing ZMQ sockets...")
        if socket:
            socket.close(linger=0)
        if ctx:
            ctx.term()
        logger.info("Core: Terminated cleanly")


if __name__ == "__main__":
    run_core_server()
