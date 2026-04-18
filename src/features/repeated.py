from __future__ import annotations

import re
from collections import defaultdict

from src.features.models import FeatureRecord
from src.models.ingestion import Block

_MIN_THRESHOLD = 3

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "will", "would", "could", "should",
    "may", "might", "this", "that", "with", "from", "for",
    "not", "but", "and", "or",
})

# Letters required, min 4 chars (includes hyphens/underscores for compound terms)
_TOKEN_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\-_]{3,}\b")


def extract_repeated_patterns(blocks: list[Block]) -> list[FeatureRecord]:
    # Map (block_type, token) → list of source blocks (one entry per distinct block)
    occurrences: dict[tuple[str, str], list[Block]] = defaultdict(list)

    for b in blocks:
        if b.gate_status == "REJECT":
            continue
        tokens = set(_tokenize(b.clean_text))
        for token in tokens:
            occurrences[(b.block_type, token)].append(b)

    records: list[FeatureRecord] = []
    for (_, token), source_blocks in occurrences.items():
        if len(source_blocks) >= _MIN_THRESHOLD:
            first = source_blocks[0]
            records.append(FeatureRecord(
                feature_type="repeated_pattern",
                value=token,
                block_id=first.block_id,
                doc_id=first.doc_id,
                page_number=first.page_number,
                frequency=len(source_blocks),
            ))
    return records


def _tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS
    ]
