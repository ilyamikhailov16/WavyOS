from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines.edge_engine import EdgeEngine
from RealtimeTTS.engines.gtts_engine import GTTSEngine, GTTSVoice
from RealtimeTTS.engines.piper_engine import PiperEngine, PiperVoice
from pathlib import Path
from app_logging import get_logger
from config import settings
import subprocess
import sys

logger = get_logger(__name__)


def _load_piper_voice_model() -> None:
    """
    Ensure the Piper voice model is present locally.

    Downloads the model using `piper.download_voices` if it is not found
    at `settings.tts.piper_voice_path`.

    Side effects:
        - Creates files in the configured directory
        - Executes a subprocess
        - Requires network access

    Raises:
        subprocess.CalledProcessError: If download fails
    """
    voice_path = Path(settings.tts.piper_voice_path)
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
    """
    High-level text-to-speech manager using RealtimeTTS.

    Initializes and prioritizes multiple TTS engines based on configuration.
    Provides a unified interface for streaming and playback.

    Attributes:
        stream: TextToAudioStream instance handling synthesis and playback.
        engines: Ordered list of initialized TTS engines.
    """

    def __init__(self) -> None:
        """Creates a TTS instance."""
        self._init_engines()

        self.stream = TextToAudioStream(
            self.engines,
            language=settings.tts.language,
        )

        logger.info("TTS initialized.")

    def _init_engines(self) -> None:
        """
        Initialize configured TTS engines in priority order.

        Engines are loaded based on `settings.tts.supported_engines`.
        The order determines fallback priority during synthesis.
        """
        supported_engines = {engine: None for engine in settings.tts.supported_engines}
        if "edge" in supported_engines:
            supported_engines["edge"] = EdgeEngine()
            logger.info("The EdgeEngine now supported by TTS.")
        if "gtts" in supported_engines:
            voice = GTTSVoice(
                language=settings.tts.language, speed=settings.tts.gtts_speed
            )
            supported_engines["gtts"] = GTTSEngine(voice)
            logger.info("The GTTSEngine now supported by TTS.")
        if "piper" in supported_engines:
            _load_piper_voice_model()
            voice = PiperVoice(settings.tts.piper_voice_path)
            supported_engines["piper"] = PiperEngine(voice=voice)
            logger.info("The PiperEngine now supported by TTS.")
        self.engines = [e for e in supported_engines.values() if e is not None]

    def play(self, text: str) -> None:
        """
        Convert text to speech and play it.

        Feeds the text into the audio stream and starts playback.

        Args:
            text: Input text to synthesize.

        Notes:
            - Playback is non-blocking.
            - Calls are executed sequentially (no overlap).
        """
        self.stream.feed(text)
        self.stream.play_async()

    def stop(self) -> None:
        """Stops the playback of the synthesized audio stream immediately."""
        if self.stream.is_playing():
            self.stream.stop()
