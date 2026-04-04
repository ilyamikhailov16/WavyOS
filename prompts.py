def build_system_prompt(command_pool: dict[str, callable]) -> str:
    commands = ", ".join(f"'{k}'" for k in command_pool)

    return (
        "You are an assistant parsing Russian voice commands. "
        "The voice input may contain mistakes or imprecisions. "
        f"Your task is to map the user's intent to exactly one of the supported commands: {commands}. "
        "Pay attention to the JSON schema, which defines the exact arguments (kwargs) each command requires. "
        "Fill the kwargs based solely on the user's input. "
        "User's input can consist of Russian and English words; you must correctly identify the language of the arguments."
        "If the text does not match any of the commands or the intent is completely unclear, "
        "output the '#' in 'command_name' and empty 'kwargs'. "
        "You must strictly and exclusively output the required JSON structure."
    )
