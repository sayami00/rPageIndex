from __future__ import annotations

from src.models.ingestion import Block

HEADING_TYPES = frozenset({"heading_1", "heading_2", "heading_3"})


def extract_headings(blocks: list[Block]) -> list[Block]:
    """Return heading blocks in document order (sorted by sequence). All gate statuses included."""
    return sorted(
        [b for b in blocks if b.block_type in HEADING_TYPES],
        key=lambda b: b.sequence,
    )
