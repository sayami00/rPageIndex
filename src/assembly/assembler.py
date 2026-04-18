from __future__ import annotations

import re

from src.assembly.models import PageRecord
from src.models.ingestion import Block

_HEADING_TYPES = frozenset({"heading_1", "heading_2", "heading_3"})
_INDEXABLE_GATES = frozenset({"PASS", "FLAG"})
_MULTI_SPACE = re.compile(r"\s+")


def build_page_record(
    doc_id: str,
    source_file: str,
    page_number: int,
    page_blocks: list[Block],
    all_features: list,   # list[FeatureRecord]
    all_tables: list,     # list[TableOutput]
) -> PageRecord:
    heading_text = _build_heading_text(page_blocks)
    body_text = _build_body_text(page_blocks)
    table_text = _build_table_text(doc_id, page_number, all_tables)
    page_search_text = _collapse(" ".join(
        part for part in [heading_text, body_text, table_text] if part
    ))

    features = [
        f for f in all_features
        if f.page_number == page_number and f.doc_id == doc_id
    ]
    tables = [
        t for t in all_tables
        if page_number in t.source_pages and t.doc_id == doc_id
    ]
    quality_floor = min((b.quality_score for b in page_blocks), default=0.0)

    return PageRecord(
        doc_id=doc_id,
        source_file=source_file,
        page_number=page_number,
        heading_text=heading_text,
        body_text=body_text,
        table_text=table_text,
        page_search_text=page_search_text,
        features=features,
        tables=tables,
        quality_floor=round(quality_floor, 4),
        block_count=len(page_blocks),
    )


def _build_heading_text(blocks: list[Block]) -> str:
    parts = [
        b.clean_text.strip()
        for b in blocks
        if b.block_type in _HEADING_TYPES
    ]
    return " ".join(parts)


def _build_body_text(blocks: list[Block]) -> str:
    parts = [
        b.clean_text.strip()
        for b in blocks
        if b.block_type == "paragraph" and b.gate_status in _INDEXABLE_GATES
    ]
    return " ".join(parts)


def _build_table_text(doc_id: str, page_number: int, all_tables: list) -> str:
    rows: list[str] = []
    for t in all_tables:
        if page_number in t.source_pages and t.doc_id == doc_id:
            rows.extend(t.search_rows)
    return " ".join(rows)


def _collapse(text: str) -> str:
    return _MULTI_SPACE.sub(" ", text).strip()
