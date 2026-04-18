import pytest
from src.tables.linker import build_table_outputs
from src.models.ingestion import Block


def _make_item(block_id: str, page: int, headers: list[str], structured: list[dict]) -> dict:
    block = Block(
        block_id=block_id,
        doc_id="doc1",
        source_file="test.pdf",
        page_number=page,
        sequence=0,
        clean_text="",
        search_text="",
        block_type="table",
        quality_score=0.8,
        gate_status="PASS",
        should_index=True,
        low_confidence=False,
        is_boilerplate=False,
        is_duplicate=False,
    )
    return {"block": block, "headers": headers, "structured": structured}


def test_single_group_produces_one_output():
    headers = ["A", "B"]
    groups = [[_make_item("b1", 1, headers, [{"A": "x", "B": "y"}])]]
    outputs = build_table_outputs(groups)
    assert len(outputs) == 1
    out = outputs[0]
    assert out.table_id == "b1"
    assert out.source_pages == [1]
    assert out.headers == headers
    assert len(out.structured) == 1
    assert len(out.search_rows) == 1


def test_multi_page_group_merges_rows():
    headers = ["Node", "IP"]
    groups = [[
        _make_item("b1", 3, headers, [{"Node": "r1", "IP": "10.0.0.1"}]),
        _make_item("b2", 4, headers, [{"Node": "r2", "IP": "10.0.0.2"}]),
    ]]
    outputs = build_table_outputs(groups)
    assert len(outputs) == 1
    out = outputs[0]
    assert out.source_pages == [3, 4]
    assert len(out.structured) == 2
    assert len(out.search_rows) == 2


def test_table_id_is_first_block_id():
    headers = ["X"]
    groups = [[
        _make_item("first_block", 1, headers, [{"X": "a"}]),
        _make_item("second_block", 2, headers, [{"X": "b"}]),
    ]]
    outputs = build_table_outputs(groups)
    assert outputs[0].table_id == "first_block"


def test_continuation_of_is_none_for_merged():
    headers = ["A"]
    groups = [[_make_item("b1", 1, headers, [{"A": "v"}])]]
    outputs = build_table_outputs(groups)
    assert outputs[0].continuation_of is None


def test_search_rows_contain_headers():
    headers = ["Node", "IP"]
    structured = [{"Node": "r1", "IP": "10.0.0.1"}]
    groups = [[_make_item("b1", 1, headers, structured)]]
    outputs = build_table_outputs(groups)
    row = outputs[0].search_rows[0]
    assert "Node" in row
    assert "IP" in row


def test_empty_groups():
    assert build_table_outputs([]) == []
