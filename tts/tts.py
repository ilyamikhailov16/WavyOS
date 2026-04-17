from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines.piper_engine import PiperEngine, PiperVoice
from .phrase_registry import CMD2VOICE
from app_logging import get_logger
from pathlib import Path
from typing import Any

logger = get_logger(__name__)
VOICE_PATH = str((Path(__name__).parent / "tts/models/piper/ru_RU-irina-medium.onnx").resolve())


class TTS:
    def __init__(self) -> None:
        self.voice = PiperVoice(VOICE_PATH)
        self.engine = PiperEngine(voice=self.voice)

        self.stream = TextToAudioStream(
            self.engine,
            language="ru",
        )

    def voice_command(self, cmd_name: str, cmd_kwargs: dict[str, Any]) -> None:
        if cmd_name not in CMD2VOICE:
            logger.warning(f"TTS doesn't support this command: {cmd_name}")

        self.play(CMD2VOICE[cmd_name].format(**cmd_kwargs))

    def play(self, text: str) -> None:
        self.stream.feed(text)
        # self.stream.play_async()
        self.stream.play(output_wavfile="piper_voicing_command.wav")
