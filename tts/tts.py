from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines.piper_engine import PiperEngine, PiperVoice
from .phrase_registry import CMD2VOICE
from pathlib import Path
from typing import Any
from app_logging import get_logger
from config import settings
import subprocess
import sys

logger = get_logger(__name__)


def _load_piper_voice_model() -> None:
    voice_path = Path(settings.tts.voice_path)
    if voice_path.is_file():
        return

    voice_dir = str(voice_path.parent)
    voice_model = voice_path.stem

    logger.info(f"Loading voice model: {voice_model}.")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "piper.download_voices",
            "--download-dir",
            voice_dir,
            voice_model,
        ],
        check=True,
    )


class TTS:
    def __init__(self) -> None:
        _load_piper_voice_model()
        self.voice = PiperVoice(settings.tts.voice_path)
        self.engine = PiperEngine(voice=self.voice)

        self.stream = TextToAudioStream(
            self.engine,
            language=settings.tts.language,
        )

        logger.info("TTS initialized.")

    def voice_command(self, cmd_name: str, cmd_kwargs: dict[str, Any]) -> None:
        if cmd_name not in CMD2VOICE:
            logger.warning(f"TTS doesn't support this command: {cmd_name}")
            return

        self.play(CMD2VOICE[cmd_name].format(**cmd_kwargs))

    def play(self, text: str) -> None:
        self.stream.feed(text)
        self.stream.play_async()
