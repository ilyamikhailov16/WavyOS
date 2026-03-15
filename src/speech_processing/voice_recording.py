import os
import queue as q
import threading as th
from typing import Callable
from RealtimeSTT import AudioToTextRecorder

# Constants
os.environ["CT2_VERBOSE"] = "-3"
EXIT_KEY = "esc"
CLEAR_COMMAND = "cls"
AUDIO_RECORDER_PARAMS = {
    "model": "tiny",  # Options: "tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2".
    "language": "ru",
    "compute_type": "default", # Quantization: int8, int8_float32, int8_float16, int8_bfloat16, int16, float16, bfloat16, float32.
    "silero_sensitivity": 0.6,
    "silero_use_onnx": True, # Recommended for faster performance.
    "silero_deactivity_detection": False, # Enables the Silero model for end-of-speech detection. More robust against background noise. When False, uses the default WebRTC VAD.
    "post_speech_silence_duration": 2.0, # Duration in seconds of silence that must follow speech before the recording is considered to be completed.
    "min_gap_between_recordings": 1.0, # Specifies the minimum time interval in seconds that should exist between the end of one recording session and the beginning of another to prevent rapid consecutive recordings.
    "min_length_of_recording": 1.0, # Specifies the minimum duration in seconds that a recording session should last to ensure meaningful audio capture, preventing excessively short or fragmented recordings.
    "pre_recording_buffer_duration": 0.2, # The time span, in seconds, during which audio is buffered prior to formal recording. This helps counterbalancing the latency inherent in speech activity detection, ensuring no initial audio is missed.
    "no_log_file": True,
    "spinner": False, # Provides a spinner animation
}

# Functions
def process_text(text: str) -> None:
    """Post-processing of the recorded text."""

    return text


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


if __name__ == "__main__":
    queue = q.Queue()
    stop_event, recorder_thread = run_voice_processing(AUDIO_RECORDER_PARAMS, queue, process_text)

    while True:
        print(queue.get())