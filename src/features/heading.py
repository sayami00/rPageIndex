from __future__ import annotations

from src.features.models import FeatureRecord
from src.models.ingestion import Block

_HEADING_TYPES = frozenset({"heading_1", "heading_2", "heading_3"})


def extract_headings(blocks: list[Block]) -> list[FeatureRecord]:
    return [
        FeatureRecord(
            feature_type="heading",
            value=b.clean_text.strip(),
            block_id=b.block_id,
            doc_id=b.doc_id,
            page_number=b.page_number,
        )
        for b in blocks
        if b.block_type in _HEADING_TYPES and b.gate_status != "REJECT"
    ]
