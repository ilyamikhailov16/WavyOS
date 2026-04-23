"""
Auxiliary logic for AppManager.

  TRANSLITERATION — ru→en table (auto-resolving Russian names)

App alias data (APP_ALIASES, APP_PROTOCOL_ALIASES, APP_CONSOLE_APPS,
APP_NAME_ALIASES) has been moved to config.AppManagerSettings.
"""

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
