"""
Словари алиасов и вспомогательные данные для AppManager.

  APP_ALIASES          — системные утилиты Windows → .exe из PATH
  APP_PROTOCOL_ALIASES — URI-протоколы (ms-settings:, epic://, …)
  APP_SPECIAL_LAUNCH   — нестандартный запуск (Valorant, Roblox)
  APP_CONSOLE_APPS     — .exe требующие CREATE_NEW_CONSOLE
  APP_KNOWN_PATHS      — пути для приложений вне реестра (Steam)
  APP_NAME_ALIASES     — алиасы → DisplayName в реестре
  TRANSLITERATION      — таблица ru→en (авто-резолв русских названий)
"""

# ---------------------------------------------------------------------------
# Системные утилиты Windows
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
# URI-протоколы — открываются через os.startfile()
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
# Консольные приложения — требуют CREATE_NEW_CONSOLE
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
# Сторонние приложения — алиас → DisplayName в реестре
# ---------------------------------------------------------------------------

APP_NAME_ALIASES: dict[str, str] = {
    # Браузеры
    "хром": "Google Chrome",
    "chrome": "Google Chrome",
    "гугл хром": "Google Chrome",
    "фаерфокс": "Mozilla Firefox",
    "firefox": "Mozilla Firefox",
    "эдж": "Microsoft Edge",
    "edge": "Microsoft Edge",
    # Мессенджеры
    "телеграм": "Telegram",
    "telegram": "Telegram",
    "дискорд": "Discord",
    "discord": "Discord",
    # Медиа
    "спотифай": "Spotify",
    "spotify": "Spotify",
    # Разработка
    "vs code": "Microsoft Visual Studio Code",
    "vscode": "Microsoft Visual Studio Code",
    "code": "Microsoft Visual Studio Code",
    "пайчарм": "PyCharm",
    "pycharm": "PyCharm",
}

# ---------------------------------------------------------------------------
# Транслитерация ru → en
# Позволяет автоматически разрешать русские названия без ручных алиасов.
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
    """Транслитерирует русский текст в латиницу."""
    return "".join(TRANSLITERATION.get(ch, ch) for ch in text.lower())
