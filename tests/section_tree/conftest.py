from __future__ import annotations

from src.models.ingestion import Block


def make_block(
    block_id: str,
    block_type: str,
    clean_text: str,
    page_number: int = 1,
    sequence: int = 0,
    gate_status: str = "PASS",
    doc_id: str = "doc1",
    source_file: str = "test.pdf",
    quality_score: float = 0.9,
) -> Block:
    return Block(
        block_id=block_id,
        doc_id=doc_id,
        source_file=source_file,
        page_number=page_number,
        sequence=sequence,
        clean_text=clean_text,
        search_text=clean_text.lower(),
        block_type=block_type,
        quality_score=quality_score,
        gate_status=gate_status,
        should_index=gate_status != "REJECT",
        low_confidence=gate_status == "FLAG",
        is_boilerplate=False,
        is_duplicate=False,
    )
