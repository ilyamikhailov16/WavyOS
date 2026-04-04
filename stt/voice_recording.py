"""Real-time voice recording and receiving the recorded text in the main stream functionality."""

import logging
import queue as q
import threading as th
from typing import Callable, Optional
from RealtimeSTT import AudioToTextRecorder
from commands_schema import Command

from app_logging import get_logger

logger: logging.Logger = get_logger(__name__)


def run_audio_recorder(
    stop_event: th.Event,
    queue: Optional[q.Queue[Command]],
    process_text_func: Optional[Callable[[str], Optional[str]]],
    **kwargs,
) -> None:
    """
    Starts AudioToTextRecorder to recognize speech and convert it to command.
    Activated by voice and stops recording after a certain length of silence at the end of a speech.
    Designed to work in a separate thread, so it waits for a stop_event.
    """

    def callback(text: str) -> None:
        try:
            if queue is None:
                return

            if process_text_func is not None:
                command = process_text_func(text)
                if command is None:
                    logger.info(
                        "The message was not processed by the processor and was ignored"
                    )
                    return

            queue.put(command)
        except Exception:
            logger.exception("Exception in STT callback")

    with AudioToTextRecorder(
        **kwargs,
        on_vad_detect_start=lambda: logger.info("VAD: you can speek"),
        on_recording_start=lambda: logger.info("recording start"),
        on_recording_stop=lambda: logger.info("recording stop"),
        on_transcription_start=lambda x: logger.info("transcription start"),
    ) as recorder:
        while not stop_event.is_set():
            recorder.text(callback)


def run_voice_processing(
    audio_recorder_params: dict,
    queue: Optional[q.Queue[str]] = None,
    process_text_func: Optional[Callable[[str], Optional[str]]] = None,
) -> tuple[th.Event, th.Thread]:
    """
    Runs the voice processing thread.
    """

    stop_event = th.Event()
    recorder_thread = th.Thread(
        target=run_audio_recorder,
        args=(stop_event, queue, process_text_func),
        kwargs=audio_recorder_params,
    )
    recorder_thread.start()
    return stop_event, recorder_thread
