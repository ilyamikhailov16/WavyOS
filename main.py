import logging
import queue as q
import threading as th
from typing import Any, Callable, Optional

from stt import LLMProcessor, run_voice_processing
from config import settings

from prompts import build_system_prompt
from app_logging import get_logger
from command_registry import COMMAND_POOL

logger: logging.Logger = get_logger(__name__)
# logging.getLogger().setLevel(logging.ERROR)

class App:
    """Main application runner for speech-to-command processing."""

    def __init__(self, cfg: Any) -> None:
        """
        Create an application instance.

        Args:
            cfg: Application configuration object (expects `.llm` and `.stt` sections).
        """

        self.cfg: Any = cfg
        self.queue: q.Queue[str] = q.Queue()
        self.text_processor: Callable[[str], str | None] = self._build_text_processor()
        self.stop_event: Optional[th.Event] = None
        self.recorder_thread: Optional[th.Thread] = None

    def _build_text_processor(self) -> Callable[[str], str | None]:
        """Build a text post-processor that maps raw STT text to a command token."""
        if self.cfg.llm.use_for_stt:
            return LLMProcessor(
                base_url=self.cfg.llm.base_url,
                api_key=self.cfg.llm.token,
                model_path=self.cfg.llm.model,
                system_prompt=build_system_prompt(COMMAND_POOL),
            )
        return lambda text: text

    def run(self) -> None:
        """Start voice processing and execute recognized commands in a loop."""
        
        self.stop_event, self.recorder_thread = run_voice_processing(
            self.cfg.stt.model_dump(), self.queue, self.text_processor
        )

        while not self.stop_event.is_set():
            command = self.queue.get()
            logger.info("Recognised: %s", command)

            command_fn = COMMAND_POOL.get(command)
            if command_fn:
                try:
                    command_fn()
                    logger.info("Work is done")
                except Exception:
                    logger.exception("Exception caught while executing command")


if __name__ == "__main__":
    app = App(settings)
    app.run()


