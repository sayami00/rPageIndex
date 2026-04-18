from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_ABBREV_FILE = Path(__file__).parent / "abbreviations.json"
_PUNCT_RE = re.compile(r"[^\w\s]")
_MULTI_SPACE = re.compile(r"\s+")


@lru_cache(maxsize=1)
def _load_abbreviations() -> dict[str, str]:
    if _ABBREV_FILE.exists():
        return json.loads(_ABBREV_FILE.read_text(encoding="utf-8"))
    return {}


def build_search_text(text: str) -> str:
    """Lowercase, expand abbreviations, strip punctuation."""
    result = text.lower()
    abbrevs = _load_abbreviations()
    for abbrev, expansion in abbrevs.items():
        result = re.sub(
            r"\b" + re.escape(abbrev.lower()) + r"\b",
            expansion.lower(),
            result,
        )
    result = _PUNCT_RE.sub(" ", result)
    result = _MULTI_SPACE.sub(" ", result).strip()
    return result
