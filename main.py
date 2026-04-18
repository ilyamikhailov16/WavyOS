import time
import logging
import queue as q
import threading as th
import asyncio
import inspect
from typing import Any, Callable, Optional

from prompts import build_command_prompt, KWARGS_PROMPT
from app_logging import get_logger
from commands.commands_registry import COMMAND_POOL

from tts import TTS
from stt import LLMProcessor, CommandProcessor, run_voice_processing
from commands.commands_schema import Command, CommandEmptyArgs
from config import settings

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
        self.tts: TTS = TTS()

    def _build_text_processor(self) -> Callable[[str], str | None]:
        """Build a text post-processor that maps raw STT text to a command token."""
        if self.cfg.llm.use_for_stt:
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
                    self.tts.voice_command(cmd_name, kwargs)
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

    def stop(self) -> None:
        """Request shutdown and wait for worker threads to finish."""

        if not self.stop_event:
            return

        self.stop_event.set()

        self.recorder_thread.join()
        self.loop_thread.join()


if __name__ == "__main__":
    app = App(settings, COMMAND_POOL)

    try:
        app.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        app.stop()
