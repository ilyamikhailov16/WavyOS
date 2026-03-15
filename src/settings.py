from scripts import empty_recycle_bin, take_screenshot

AUDIO_RECORDER_PARAMS = {
    # Options: "tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2".
    "model": "medium",
    "language": "ru",
    # Quantization: int8, int8_float32, int8_float16, int8_bfloat16, int16, float16, bfloat16, float32.
    "compute_type": "float32",
    "silero_sensitivity": 0.6,
    "silero_use_onnx": True,  # Recommended for faster performance.
    # Enables the Silero model for end-of-speech detection. More robust against background noise. When False, uses the default WebRTC VAD.
    "silero_deactivity_detection": False,
    # Duration in seconds of silence that must follow speech before the recording is considered to be completed.
    "post_speech_silence_duration": 2.0,
    # Specifies the minimum time interval in seconds that should exist between the end of one recording session and the beginning of another to prevent rapid consecutive recordings.
    "min_gap_between_recordings": 1.0,
    # Specifies the minimum duration in seconds that a recording session should last to ensure meaningful audio capture, preventing excessively short or fragmented recordings.
    "min_length_of_recording": 1.0,
    # The time span, in seconds, during which audio is buffered prior to formal recording. This helps counterbalancing the latency inherent in speech activity detection, ensuring no initial audio is missed.
    "pre_recording_buffer_duration": 0.2,
    "no_log_file": True,
    "spinner": True,  # Provides a spinner animation
}
API_KEY = ""
MODEL_OPENROUTER_PATH = "openai/gpt-oss-20b"
COMMAND_POOL = {"Очистить корзину": empty_recycle_bin, "Скриншот": take_screenshot}
SYSTEM_PROMPT = ("Ты получишь на вход текст на русском языке. "
                 "Очень вероятно, что текст будет содержать ошибки и окажется неточным. "
                f"Твоя задача - проверить подходит ли текст под одну из данных команд, если исправить в нём ошибки: {", ".join(f"'{k}'" for k in COMMAND_POOL.keys())}. " 
                 "Тебе необходимо вывести ту, с которой он сопоставим. "
                 "В ответе должна быть лишь эта найденная команда и ничего больше. "
                 "Если ни одна команда не является подходящей, то вместо неё в ответе дай символ: #. "
                 "Точку после ответа добавлять не надо."
                )