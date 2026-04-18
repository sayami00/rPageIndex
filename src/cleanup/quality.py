from __future__ import annotations

import re

# Junk: replacement char, long dash runs, control chars, repeated question marks.
# Normal punctuation (.,;:-) is intentionally excluded.
_JUNK_RE = re.compile(r"\ufffd|[-]{4,}|[\x00-\x1f]|\?{3,}")

_REJECT_THRESHOLD = 0.40
_FLAG_THRESHOLD = 0.65


def compute_quality_score(text: str, is_boilerplate: bool) -> float:
    if not text:
        return 0.0

    total = len(text)

    length_score = min(total / 200, 1.0)

    alpha_count = sum(1 for c in text if c.isalpha())
    alpha_ratio = alpha_count / total

    boilerplate_flag = 0.0 if is_boilerplate else 1.0

    junk_chars = sum(len(m) for m in _JUNK_RE.findall(text))
    junk_ratio = junk_chars / total

    score = (
        0.30 * length_score
        + 0.30 * alpha_ratio
        + 0.20 * boilerplate_flag
        + 0.20 * (1.0 - junk_ratio)
    )
    return round(min(max(score, 0.0), 1.0), 4)


def compute_gate_status(score: float) -> str:
    if score < _REJECT_THRESHOLD:
        return "REJECT"
    if score <= _FLAG_THRESHOLD:
        return "FLAG"
    return "PASS"
