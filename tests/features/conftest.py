"""Shared Block factory for feature extraction tests."""
from __future__ import annotations

import pytest
from src.models.ingestion import Block


def make_block(
    block_id: str = "doc_p0001_s0000",
    doc_id: str = "doc1",
    clean_text: str = "Sample text content here.",
    block_type: str = "paragraph",
    gate_status: str = "PASS",
    page_number: int = 1,
    sequence: int = 0,
) -> Block:
    return Block(
        block_id=block_id,
        doc_id=doc_id,
        source_file="test.pdf",
        page_number=page_number,
        sequence=sequence,
        clean_text=clean_text,
        search_text=clean_text.lower(),
        block_type=block_type,
        quality_score=0.8,
        gate_status=gate_status,
        should_index=gate_status != "REJECT",
        low_confidence=gate_status == "FLAG",
        is_boilerplate=False,
        is_duplicate=False,
    )
