import pytest
from src.tables.detector import filter_table_blocks, _is_pseudo_table
from src.models.ingestion import Block


def _make_block(
    block_type: str = "table",
    gate_status: str = "PASS",
    clean_text: str = "Node | IP | Status\nr1 | 10.0.0.1 | active",
) -> Block:
    return Block(
        block_id="testdoc_p0001_s0000",
        doc_id="testdoc",
        source_file="test.pdf",
        page_number=1,
        sequence=0,
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


def test_keeps_valid_table_block():
    blocks = [_make_block()]
    result = filter_table_blocks(blocks)
    assert len(result) == 1


def test_drops_non_table_blocks():
    blocks = [_make_block(block_type="paragraph")]
    result = filter_table_blocks(blocks)
    assert len(result) == 0


def test_drops_rejected_table():
    blocks = [_make_block(gate_status="REJECT")]
    result = filter_table_blocks(blocks)
    assert len(result) == 0


def test_keeps_flagged_table():
    blocks = [_make_block(gate_status="FLAG")]
    result = filter_table_blocks(blocks)
    assert len(result) == 1


def test_drops_pseudo_table_no_separator():
    blocks = [_make_block(clean_text="Just some paragraph text without any pipes")]
    result = filter_table_blocks(blocks)
    assert len(result) == 0


def test_drops_single_column_table():
    blocks = [_make_block(clean_text="Header\nrow1\nrow2\nrow3")]
    result = filter_table_blocks(blocks)
    assert len(result) == 0


def test_is_pseudo_table_no_pipe():
    assert _is_pseudo_table("plain text no separator") is True


def test_is_pseudo_table_has_pipe():
    assert _is_pseudo_table("col1 | col2\nval1 | val2") is False


def test_tab_separated_not_pseudo():
    assert _is_pseudo_table("col1\tcol2\nval1\tval2") is False
