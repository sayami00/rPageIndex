from __future__ import annotations

from src.features.models import FeatureRecord
from src.models.ingestion import Block


def extract_bullet_items(blocks: list[Block]) -> list[FeatureRecord]:
    return [
        FeatureRecord(
            feature_type="bullet_item",
            value=b.clean_text.strip(),
            block_id=b.block_id,
            doc_id=b.doc_id,
            page_number=b.page_number,
        )
        for b in blocks
        if b.block_type == "list_item" and b.gate_status != "REJECT"
    ]
