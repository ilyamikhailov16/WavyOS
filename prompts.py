def build_system_prompt(command_pool: dict[str, callable]) -> str:
    commands = ", ".join(f"'{k}'" for k in command_pool)

    return (
        "You will receive a text in Russian as input. "
        "It is very likely that the text will contain mistakes and be imprecise. "
        "Your task is to determine whether the text matches one of the following commands "
        f"after correcting its mistakes: {commands}. "
        "You must output the single command it maps to, and nothing else. "
        "If none of the commands are suitable, output the symbol: #. "
        "Do not add a period after the answer."
    )