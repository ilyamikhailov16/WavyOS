"""Real-time voice recording and receiving the recorded text in the main stream functionality."""

import logging
import queue as q
import threading as th
import time
from pathlib import Path
from typing import Callable, Optional

from RealtimeSTT import AudioToTextRecorder
from commands.commands_schema import Command
from config.settings import ROOT_DIR

import soundfile as sf

from app_logging import get_logger

logger: logging.Logger = get_logger(__name__)
DEBUG_AUDIO_DIR = ROOT_DIR / "stt_debug"


def _save_debug_audio(audio_data) -> Path | None:
    """Persist the latest transcribed audio chunk for debugging STT issues."""

    if audio_data is None:
        return None

    DEBUG_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_AUDIO_DIR / f"last_recording_{time.strftime('%Y%m%d_%H%M%S')}.wav"
    sf.write(str(path), audio_data, 16000)
    return path


def run_audio_recorder(
    stop_event: th.Event,
    queue: Optional[q.Queue[Command]],
    process_text_func: Optional[Callable[[str], Optional[str]]],
    status_callback: Optional[Callable[[str], None]] = None,
    **kwargs,
) -> None:
    """
    Starts AudioToTextRecorder to recognize speech and convert it to command.
    Activated by voice and stops recording after a certain length of silence at the end of a speech.
    Designed to work in a separate thread, so it waits for a stop_event.
    """

    def emit_status(status: str) -> None:
        if status_callback is None:
            return
        try:
            status_callback(status)
        except Exception:
            logger.exception("Exception in STT status callback")

    def callback(text: str) -> None:
        try:
            if queue is None:
                return

            logger.info("Raw STT text: %s", text)
            if text is None:
                logger.info("STT returned no text; skipping command processing")
                return
            if not isinstance(text, str):
                logger.info("STT returned unexpected payload %r; skipping", type(text))
                return
            if not text.strip():
                logger.info("STT returned empty text; skipping command processing")
                return

            if process_text_func is not None:
                command = process_text_func(text)
                if command is None:
                    logger.info(
                        "The message was not processed by the processor and was ignored"
                    )
                    emit_status("processing_error")
                    return

            queue.put(command)
        except Exception:
            emit_status("processing_error")
            logger.exception("Exception in STT callback")

    def on_transcription_start(audio_data) -> None:
        logger.info("transcription start")
        emit_status("transcription_started")
        try:
            path = _save_debug_audio(audio_data)
            if path is not None:
                logger.info("Saved STT debug audio: %s", path)
        except Exception:
            logger.exception("Failed to save STT debug audio")

    with AudioToTextRecorder(
        **kwargs,
        on_vad_detect_start=lambda: (
            logger.info("VAD: you can speek"),
            emit_status("listening_started"),
        ),
        on_recording_start=lambda: logger.info("recording start"),
        on_recording_stop=lambda: (
            logger.info("recording stop"),
            emit_status("recording_stopped"),
        ),
        on_transcription_start=on_transcription_start,
    ) as recorder:
        while not stop_event.is_set():
            recorder.text(callback)


def run_voice_processing(
    audio_recorder_params: dict,
    queue: Optional[q.Queue[str]] = None,
    process_text_func: Optional[Callable[[str], Optional[str]]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> tuple[th.Event, th.Thread]:
    """
    Runs the voice processing thread.
    """

    stop_event = th.Event()
    recorder_thread = th.Thread(
        target=run_audio_recorder,
        args=(stop_event, queue, process_text_func),
        kwargs={**audio_recorder_params, "status_callback": status_callback},
        daemon=True,
    )
    recorder_thread.start()
    return stop_event, recorder_thread
