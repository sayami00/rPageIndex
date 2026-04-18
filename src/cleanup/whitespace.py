from __future__ import annotations

import re
import unicodedata

MIN_TEXT_LENGTH = 5

_HORIZONTAL_SPACE = re.compile(r"[ \t]+")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def clean_whitespace(text: str) -> str | None:
    """NFC-normalize, collapse whitespace. Returns None if result < MIN_TEXT_LENGTH."""
    text = unicodedata.normalize("NFC", text)
    text = text.strip()
    text = _HORIZONTAL_SPACE.sub(" ", text)
    text = _EXCESS_BLANK_LINES.sub("\n\n", text)
    if len(text) < MIN_TEXT_LENGTH:
        return None
    return text
