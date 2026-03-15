import logging
import queue as q
from settings import *
from speech_processing import *

logging.getLogger().setLevel(logging.ERROR)

if __name__ == "__main__":
    queue = q.Queue()
    text_processor = LLMProcessor(API_KEY, MODEL_OPENROUTER_PATH, SYSTEM_PROMPT) 
    stop_event, recorder_thread = run_voice_processing(AUDIO_RECORDER_PARAMS, queue, text_processor)

    while True:
        command = queue.get()
        print(f"\nRecognised: {command}")

        for command_key, script_value in COMMAND_POOL.items():
            if command == command_key:
                script_value()
                print(f"Work is done")