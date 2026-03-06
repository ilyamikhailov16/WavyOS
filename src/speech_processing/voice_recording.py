import os
import keyboard
import threading as th
from RealtimeSTT import AudioToTextRecorder

# Constants
os.environ['CT2_VERBOSE'] = '-3'
AUDIO_RECORDER_PARAMS = {
    "model": "tiny",
    "language": "ru",
    "enable_realtime_transcription": False,
    "no_log_file": True,
}
EXIT_KEY = 'esc'

# Functions
def process_text(text: str) -> None:
    """Post-processing of the recorded text."""

    print(text)


def run_audio_recorder(stop_event, *args, **kwargs) -> None:
    """
    Starts AudioToTextRecorder to recognize speech and convert it to text.
    Activated by voice and stops recording after a certain length of silence at the end of a speech.
    Designed to work in a separate thread, so it waits for a stop_event.
    """
    
    with AudioToTextRecorder(*args, **kwargs) as recorder:
        while not stop_event.is_set():
            recorder.text(process_text)


def run_voice_processing(audio_recorder_params: dict, exit_key: str) -> None:
    """
    Runs the voice processing thread.
    Blocks the thread in which it is called.
    Terminates when 'esc' is pressed.
    """

    stop_event = th.Event()
    recorder_thread = th.Thread(
        target=run_audio_recorder, 
        args=[stop_event],
        kwargs=audio_recorder_params, 
    )

    recorder_thread.start()
    print("\nPress 'esc' to exit")
    keyboard.wait(exit_key)
    print("\nWait for completion. Your requests will no longer be processed")
    stop_event.set()
    recorder_thread.join()


if __name__ == '__main__':
    run_voice_processing(AUDIO_RECORDER_PARAMS, EXIT_KEY)