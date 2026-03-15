import os

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
API_KEY = ""
MODEL_OPENROUTER_PATH = "mistralai/mistral-nemo"
SYSTEM_PROMPT = "Any text that comes in to you, you must replace it with 16 question marks."