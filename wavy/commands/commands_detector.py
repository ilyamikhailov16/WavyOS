from __future__ import annotations

import re
import unicodedata
from typing import Optional

from rapidfuzz import fuzz

from .commands_registry import COMMAND_INFO

import logging
logger = logging.Logger("commands_detector")


def _normalize_for_match(text: str) -> str:
    """
    Normalize only for command matching:
    - Unicode normalize
    - casefold for better lowercase handling
    - ё -> е
    - hyphens/punctuation -> spaces
    - collapse whitespace
    """
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    text = re.sub(r"[^\w\s-]+", " ", text, flags=re.UNICODE)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    clean = _normalize_for_match(text)
    return clean.split() if clean else []


def _best_command_match(text: str, threshold: float = 80) -> tuple[Optional[str], int]:
    """
    Returns:
        (cmd_name, consumed_token_count)

    Assumption:
        command is usually at the beginning of the sentence.
        This is the safest design for voice/assistant commands.
    """
    clean = _normalize_for_match(text)
    if not clean:
        return None, 0

    print(f"Normalized command: {clean}")

    tokens = clean.split()
    if not tokens:
        return None, 0

    best_cmd: Optional[str] = None
    best_score = -1.0
    best_consumed = 0
    best_exact = False

    for cmd_name in COMMAND_INFO.keys():
        cmd_clean = _normalize_for_match(cmd_name)
        cmd_tokens = cmd_clean.split()
        if not cmd_tokens:
            continue

        # 1) Exact boundary match anywhere in the normalized text
        exact = re.search(rf"(?<!\w){re.escape(cmd_clean)}(?!\w)", clean)

        print("Is exact:", bool(exact))

        if exact:
            score = 100.0 + len(cmd_tokens) * 0.01
            consumed = len(cmd_tokens)
            is_exact = True
            print("Exact:", cmd_name, score, consumed)
        else:
            # 2) Fuzzy match only against the beginning of the text.
            # This is robust for typos in commands and keeps arg extraction simple.
            prefix_window = " ".join(tokens[: min(len(tokens), len(cmd_tokens) + 2)])
            score = float(fuzz.partial_ratio(cmd_clean, prefix_window))
            consumed = len(cmd_tokens)
            is_exact = False

            print("Fuzzy:", cmd_name, score, consumed, prefix_window)

        if (
            score > best_score
            or (score == best_score and is_exact and not best_exact)
            or (
                score == best_score
                and len(cmd_tokens) > len(_normalize_for_match(best_cmd or "").split())
            )
        ):
            best_cmd = cmd_name
            best_score = score
            best_consumed = consumed
            best_exact = is_exact

    print(f"Fuzzy match best score: {best_score}")

    if best_score >= threshold:
        return best_cmd, best_consumed

    return None, 0


def _extract_args_after_command(text: str, consumed_tokens: int) -> str:
    """
    Best-effort arg extraction assuming the command is at the start.
    Keeps the original token text, only strips the leading command tokens.
    """
    raw_tokens = text.strip().split()
    if consumed_tokens >= len(raw_tokens):
        return ""
    return " ".join(raw_tokens[consumed_tokens:]).strip()
