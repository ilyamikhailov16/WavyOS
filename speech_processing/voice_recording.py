"""Real-time voice recording and receiving the recorded text in the main stream functionality."""

import queue as q
import threading as th
from typing import Callable
from RealtimeSTT import AudioToTextRecorder


def run_audio_recorder(stop_event: th.Event, queue: q.Queue, process_text_func: Callable, **kwargs) -> None:
    """
    Starts AudioToTextRecorder to recognize speech and convert it to text.
    Activated by voice and stops recording after a certain length of silence at the end of a speech.
    Designed to work in a separate thread, so it waits for a stop_event.
    """

    def callback(text: str) -> None:
        if queue is not None:
            if process_text_func is not None:
                text = process_text_func(text)
            queue.put(text)
    
    with AudioToTextRecorder(**kwargs) as recorder:
        while not stop_event.is_set():
            recorder.text(callback)


def run_voice_processing(audio_recorder_params: dict, queue: q.Queue = None, process_text_func: Callable = None) -> tuple[th.Event, th.Thread]:
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