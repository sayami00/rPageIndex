from __future__ import annotations

import re

from src.features.models import FeatureRecord
from src.models.ingestion import Block

_PATTERNS: dict[str, re.Pattern] = {
    "ip":       re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "version":  re.compile(r"\bv?\d+\.\d+(?:\.\d+)*(?:-[\w.]+)?\b"),
    "hostname": re.compile(r"\b[a-zA-Z][a-zA-Z0-9\-]*(?:\.[a-zA-Z0-9\-]+)*\.[a-zA-Z]{2,6}\b"),
}


def extract_named_entities(blocks: list[Block]) -> list[FeatureRecord]:
    seen: set[tuple[str, str, str]] = set()  # (value, subtype, doc_id)
    records: list[FeatureRecord] = []

    for b in blocks:
        if b.gate_status == "REJECT":
            continue
        for subtype, pattern in _PATTERNS.items():
            for m in pattern.finditer(b.clean_text):
                val = m.group(0)
                dedup_key = (val, subtype, b.doc_id)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                records.append(FeatureRecord(
                    feature_type="named_entity",
                    value=val,
                    block_id=b.block_id,
                    doc_id=b.doc_id,
                    page_number=b.page_number,
                    entity_subtype=subtype,
                ))
    return records
