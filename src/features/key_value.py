from __future__ import annotations

import re

from src.features.models import FeatureRecord
from src.models.ingestion import Block

_KV_RE = re.compile(r"^([^:\n]{2,80}):\s+(.+)$", re.MULTILINE)
_KEY_HAS_LETTER = re.compile(r"[a-zA-Z]")

_KV_SOURCE_TYPES = frozenset({"paragraph", "heading_1", "heading_2", "heading_3"})


def extract_key_value_pairs(blocks: list[Block]) -> list[FeatureRecord]:
    records: list[FeatureRecord] = []
    for b in blocks:
        if b.block_type not in _KV_SOURCE_TYPES:
            continue
        if b.gate_status == "REJECT":
            continue
        for m in _KV_RE.finditer(b.clean_text):
            key = m.group(1).strip()
            val = m.group(2).strip()
            if not _KEY_HAS_LETTER.search(key):
                continue
            records.append(FeatureRecord(
                feature_type="key_value_pair",
                value=f"{key}: {val}",
                block_id=b.block_id,
                doc_id=b.doc_id,
                page_number=b.page_number,
                key=key,
            ))
    return records
