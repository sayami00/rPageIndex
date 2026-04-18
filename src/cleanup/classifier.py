from __future__ import annotations

import re

_HEADING_MAX_LEN = 120
_HEADING_MAX_WORDS = 15
_BULLET_RE = re.compile(r"^[\-\*\•\◦\–\—\►\▪\·]\s+")
_NUMBERED_RE = re.compile(r"^\d+[\.\)]\s+")
_TABLE_TAB_RE = re.compile(r"\t")
_PAGE_NUM_RE = re.compile(r"^(page\s+)?\d+(\s*of\s*\d+)?$", re.IGNORECASE)
_CAPTION_RE = re.compile(r"^(figure|fig\.?|table|tab\.?|chart|exhibit)\s+\d+", re.IGNORECASE)
_TERMINAL_PUNCT_RE = re.compile(r"[.!?;]$")

_HEADING_HINTS = {"heading_1", "heading_2", "heading_3", "heading"}


def classify_block(text: str, type_hint: str = "") -> str:
    """Assign block_type from parser hints and text heuristics."""
    stripped = text.strip()

    # Trust parser for tables
    if type_hint == "table":
        return "table"

    # Trust explicit heading hints from parser
    if type_hint in ("heading_1", "heading_2", "heading_3"):
        return type_hint

    # Page number
    if _PAGE_NUM_RE.match(stripped):
        return "page_number"

    # Caption
    if _CAPTION_RE.match(stripped):
        return "caption"

    # List items
    if _BULLET_RE.match(stripped) or _NUMBERED_RE.match(stripped):
        return "list_item"

    # Table: heavy tab usage
    if _TABLE_TAB_RE.search(stripped):
        return "table"

    # Heading heuristic: short, no sentence-ending punctuation, single line
    if (
        len(stripped) <= _HEADING_MAX_LEN
        and "\n" not in stripped
        and not _TERMINAL_PUNCT_RE.search(stripped)
        and 1 <= len(stripped.split()) <= _HEADING_MAX_WORDS
    ):
        if stripped == stripped.upper() and re.sub(r"[\s\d\W]", "", stripped):
            return "heading_1"
        if type_hint == "heading":
            return "heading_2"

    return "paragraph"
