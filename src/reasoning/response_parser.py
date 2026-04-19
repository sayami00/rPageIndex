from __future__ import annotations

import re

_INT_RE = re.compile(r"\b(\d+)\b")


def parse_selected_numbers(response: str, max_n: int) -> list[int]:
    """
    Extract 1-based candidate indices from Ollama response text.
    Returns deduped list in ascending order.
    Returns [] if no valid numbers found (triggers caller fallback).
    """
    seen: set[int] = set()
    result: list[int] = []
    for m in _INT_RE.finditer(response):
        n = int(m.group(1))
        if 1 <= n <= max_n and n not in seen:
            seen.add(n)
            result.append(n)
    result.sort()
    return result
