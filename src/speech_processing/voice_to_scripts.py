import queue as q
from settings import *
from llm_post_processing import LLMProcessor
from voice_recording import run_voice_processing

if __name__ == "__main__":
    queue = q.Queue()
    text_processor = LLMProcessor(API_KEY, MODEL_OPENROUTER_PATH, SYSTEM_PROMPT) 
    stop_event, recorder_thread = run_voice_processing(AUDIO_RECORDER_PARAMS, queue, text_processor)

    while True:
        print(queue.get())