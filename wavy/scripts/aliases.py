"""
Alias dictionaries and auxiliary data for AppManager.

  APP_ALIASES          — Windows system utilities → .exe from PATH
  APP_PROTOCOL_ALIASES — URI protocols (ms-settings:, epic://, …)
  APP_SPECIAL_LAUNCH   — custom launch (Valorant, Roblox)
  APP_CONSOLE_APPS     — .exe requiring CREATE_NEW_CONSOLE
  APP_KNOWN_PATHS      — paths for applications outside the registry (Steam)
  APP_NAME_ALIASES     — aliases → DisplayName in registry
  TRANSLITERATION      — ru→en table (auto-resolving Russian names)
"""

# ---------------------------------------------------------------------------
# Windows system utilities
# ---------------------------------------------------------------------------

APP_ALIASES: dict[str, str] = {
    "блокнот": "notepad.exe",
    "notepad": "notepad.exe",
    "калькулятор": "calc.exe",
    "calc": "calc.exe",
    "проводник": "explorer.exe",
    "explorer": "explorer.exe",
    "командная строка": "cmd.exe",
    "cmd": "cmd.exe",
    "терминал": "wt.exe",
    "terminal": "wt.exe",
    "диспетчер задач": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "реестр": "regedit.exe",
    "regedit": "regedit.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "wordpad": "wordpad.exe",
}

# ---------------------------------------------------------------------------
# URI-protocols — can be opened with os.startfile()
# ---------------------------------------------------------------------------

APP_PROTOCOL_ALIASES: dict[str, str] = {
    "settings": "ms-settings:",
    "настройки": "ms-settings:",
    "магазин": "ms-windows-store:",
    "store": "ms-windows-store:",
    "epic": "com.epicgames.launcher://",
    "epic games": "com.epicgames.launcher://",
    "эпик": "com.epicgames.launcher://",
    "эпик геймс": "com.epicgames.launcher://",
    "xbox": "xbox:",
    "иксбокс": "xbox:",
}

# ---------------------------------------------------------------------------
# Console application — require CREATE_NEW_CONSOLE
# ---------------------------------------------------------------------------

APP_CONSOLE_APPS: frozenset[str] = frozenset(
    {
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "wsl.exe",
        "python.exe",
        "pythonw.exe",
        "node.exe",
    }
)

# ---------------------------------------------------------------------------
# Other application — alias → DisplayName in register
# ---------------------------------------------------------------------------

APP_NAME_ALIASES: dict[str, str] = {
    # Browsers
    "хром": "Google Chrome",
    "chrome": "Google Chrome",
    "гугл хром": "Google Chrome",
    "фаерфокс": "Mozilla Firefox",
    "firefox": "Mozilla Firefox",
    "эдж": "Microsoft Edge",
    "edge": "Microsoft Edge",
    # Messengers
    "телеграм": "Telegram",
    "telegram": "Telegram",
    "дискорд": "Discord",
    "discord": "Discord",
    # Media
    "спотифай": "Spotify",
    "spotify": "Spotify",
    # Development
    "vs code": "Microsoft Visual Studio Code",
    "vscode": "Microsoft Visual Studio Code",
    "code": "Microsoft Visual Studio Code",
    "пайчарм": "PyCharm",
    "pycharm": "PyCharm",
}

# ---------------------------------------------------------------------------
# Transliteration ru → en
# Allows Russian names to be resolved automatically without manual aliases.
# "стим" → "stim" → fuzzy-поиск → "steam"
# ---------------------------------------------------------------------------

TRANSLITERATION: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def transliterate(text: str) -> str:
    """Transliterates Russian text into the Latin alphabet."""
    return "".join(TRANSLITERATION.get(ch, ch) for ch in text.lower())
