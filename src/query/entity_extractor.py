from __future__ import annotations

import re

from src.query.models import ExtractedEntity

# Priority order matters: ip before hostname (both have dots), version before node
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ip",       re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("hostname", re.compile(r"\b[a-zA-Z][a-zA-Z0-9\-]*(?:\.[a-zA-Z0-9\-]+)*\.[a-zA-Z]{2,15}\b")),
    ("version",  re.compile(r"\bv?\d+\.\d+(?:\.\d+)*(?:-[\w.]+)?\b")),
    ("node",     re.compile(
        r"\b(?:web|db|srv|app|cache|gw|proxy|lb|dns|mail|nfs|nas|mon|bkp)"
        r"[a-z0-9\-]*\d+\b",
        re.IGNORECASE,
    )),
]


def extract_entities(query: str) -> list[ExtractedEntity]:
    """
    Extract structured entities from query string.
    Non-overlapping — first match (by priority order) wins for any span.
    """
    taken: list[tuple[int, int]] = []  # claimed spans
    entities: list[ExtractedEntity] = []

    for entity_type, pattern in _PATTERNS:
        for m in pattern.finditer(query):
            start, end = m.start(), m.end()
            # Skip if overlaps with already-claimed span
            if any(s < end and start < e for s, e in taken):
                continue
            taken.append((start, end))
            entities.append(ExtractedEntity(
                value=m.group(0),
                entity_type=entity_type,
                start=start,
                end=end,
            ))

    # Return in document order
    entities.sort(key=lambda e: e.start)
    return entities
