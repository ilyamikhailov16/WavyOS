from pathlib import Path
from app_logging import get_logger
from config import settings
import shutil
import subprocess
import sys

logger = get_logger(__name__)

TextToAudioStream = None
EdgeEngine = None
GTTSEngine = None
GTTSVoice = None
PiperEngine = None
PiperVoice = None


def _find_executable(executable_name: str) -> str | None:
    executable = shutil.which(executable_name)
    if executable:
        return executable

    script_name = executable_name
    if sys.platform == "win32" and not script_name.endswith(".exe"):
        script_name = f"{script_name}.exe"

    local_executable = Path(sys.prefix) / "Scripts" / script_name
    if local_executable.is_file():
        return str(local_executable)

    return None


def _load_realtime_tts() -> bool:
    global TextToAudioStream
    global EdgeEngine
    global GTTSEngine
    global GTTSVoice
    global PiperEngine
    global PiperVoice

    if TextToAudioStream is not None:
        return True

    try:
        from RealtimeTTS import TextToAudioStream as stream_cls
        from RealtimeTTS.engines.edge_engine import EdgeEngine as edge_cls
        from RealtimeTTS.engines.gtts_engine import GTTSEngine as gtts_cls
        from RealtimeTTS.engines.gtts_engine import GTTSVoice as gtts_voice_cls
        from RealtimeTTS.engines.piper_engine import PiperEngine as piper_cls
        from RealtimeTTS.engines.piper_engine import PiperVoice as piper_voice_cls
    except Exception as exc:
        logger.warning("RealtimeTTS is unavailable; voice output is disabled: %s", exc)
        return False

    TextToAudioStream = stream_cls
    EdgeEngine = edge_cls
    GTTSEngine = gtts_cls
    GTTSVoice = gtts_voice_cls
    PiperEngine = piper_cls
    PiperVoice = piper_voice_cls
    return True


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
        if _load_realtime_tts():
            self._init_engines()
        else:
            self.engines = []

        if self.engines:
            self.stream = TextToAudioStream(
                self.engines,
                language=settings.tts.language,
            )
        else:
            self.stream = None

        logger.info("TTS initialized.")

    def _init_engines(self) -> None:
        """
        Initialize configured TTS engines in priority order.

        Engines are loaded based on `settings.tts.supported_engines`.
        The order determines fallback priority during synthesis.
        """
        supported_engines = {engine: None for engine in settings.tts.supported_engines}
        mpv_available = _find_executable("mpv") is not None

        if "edge" in supported_engines:
            if mpv_available:
                supported_engines["edge"] = EdgeEngine()
                logger.info("The EdgeEngine now supported by TTS.")
            else:
                logger.warning("Skipping EdgeEngine because mpv is not available.")

        if "gtts" in supported_engines:
            if mpv_available:
                voice = GTTSVoice(
                    language=settings.tts.language, speed=settings.tts.gtts_speed
                )
                supported_engines["gtts"] = GTTSEngine(voice)
                logger.info("The GTTSEngine now supported by TTS.")
            else:
                logger.warning("Skipping GTTSEngine because mpv is not available.")

        if "piper" in supported_engines:
            piper_path = _find_executable("piper")
            if piper_path:
                _load_piper_voice_model()
                voice = PiperVoice(settings.tts.piper_voice_path)
                supported_engines["piper"] = PiperEngine(
                    piper_path=piper_path,
                    voice=voice,
                )
                logger.info("The PiperEngine now supported by TTS.")
            else:
                logger.warning("Skipping PiperEngine because piper executable is not available.")

        self.engines = [e for e in supported_engines.values() if e is not None]
        if not self.engines:
            logger.warning("No playable TTS engines are available; voice output is disabled.")

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
        if self.stream is None:
            logger.warning("TTS playback skipped because no audio engine is available.")
            return

        try:
            self.stream.feed(text)
            self.stream.play_async()
        except ValueError as exc:
            logger.warning("TTS playback skipped: %s", exc)

    def stop(self) -> None:
        """Stops the playback of the synthesized audio stream immediately."""
        if self.stream is not None and self.stream.is_playing():
            self.stream.stop()
