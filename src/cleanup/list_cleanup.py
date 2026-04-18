from __future__ import annotations

import re

_BULLET_MAP: dict[str, str] = {
    "\u2022": "-",  # •
    "\u25e6": "-",  # ◦
    "\u25aa": "-",  # ▪
    "\u25b6": "-",  # ▶
    "\u25ba": "-",  # ►
    "\u00b7": "-",  # ·
    "\u2013": "-",  # –
    "\u2014": "-",  # —
    "*": "-",
}
_BULLET_RE = re.compile(r"^([\u2022\u25e6\u25aa\u25b6\u25ba\u00b7\u2013\u2014*])\s+")
_NUMBERED_RE = re.compile(r"^\d+[\.\)]\s+")


def normalize_list_item(text: str) -> tuple[str, str]:
    """Normalize bullet character and detect list kind.

    Returns (normalized_text, list_kind) where list_kind is 'ordered' or 'unordered'.
    """
    m = _BULLET_RE.match(text)
    if m:
        char = m.group(1)
        replacement = _BULLET_MAP.get(char, "-")
        normalized = replacement + " " + text[m.end():]
        return normalized, "unordered"

    if _NUMBERED_RE.match(text):
        return text, "ordered"

    return text, "unordered"
