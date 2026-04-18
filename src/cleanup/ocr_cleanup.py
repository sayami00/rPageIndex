from __future__ import annotations

import re

OCR_CONFIDENCE_LOW_THRESHOLD = 0.6

# Word-context substitutions: digit that looks like a letter, surrounded by alpha chars.
# Applied only at word boundaries to avoid corrupting numbers.
_SUBS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b0([A-Za-z])"), r"O\1"),   # 0pen → Open
    (re.compile(r"([A-Za-z])0\b"), r"\1O"),   # wOrd0 → wOrdO (rare but covered)
    (re.compile(r"\b1([A-Za-z])"), r"I\1"),   # 1nstead → Instead
    (re.compile(r"([A-Za-z])1\b"), r"\1I"),   # bui1t → buiIt
]


def fix_ocr_text(text: str) -> str:
    for pattern, replacement in _SUBS:
        text = pattern.sub(replacement, text)
    return text


def is_low_confidence(ocr_confidence: float | None) -> bool:
    if ocr_confidence is None:
        return False
    return ocr_confidence < OCR_CONFIDENCE_LOW_THRESHOLD
