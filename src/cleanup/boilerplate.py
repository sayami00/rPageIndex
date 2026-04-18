from __future__ import annotations

import re
from pathlib import Path

_PATTERNS_FILE = Path(__file__).parent / "boilerplate_patterns.txt"

_BUILTIN_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d+$"),
    re.compile(r"©|copyright", re.IGNORECASE),
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"\bconfidential\b", re.IGNORECASE),
    re.compile(r"^page\s+\d+\s*(of\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^draft$", re.IGNORECASE),
    re.compile(r"^(internal use only|proprietary)$", re.IGNORECASE),
    re.compile(r"^www\.", re.IGNORECASE),
]


def _load_corpus_patterns() -> list[re.Pattern]:
    if not _PATTERNS_FILE.exists():
        return []
    patterns = []
    for line in _PATTERNS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                patterns.append(re.compile(line, re.IGNORECASE))
            except re.error:
                pass
    return patterns


def is_boilerplate(text: str) -> bool:
    stripped = text.strip()
    all_patterns = _BUILTIN_PATTERNS + _load_corpus_patterns()
    return any(p.search(stripped) for p in all_patterns)
