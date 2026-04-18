import pytest
from src.tables.multi_page import group_continuations
from src.models.ingestion import Block


def _make_item(
    block_id: str,
    page: int,
    headers: list[str],
    structured: list[dict],
    doc_id: str = "doc1",
) -> dict:
    block = Block(
        block_id=block_id,
        doc_id=doc_id,
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


def test_single_table_no_grouping():
    items = [_make_item("b1", 1, ["A", "B"], [{"A": "x", "B": "y"}])]
    groups = group_continuations(items)
    assert len(groups) == 1
    assert len(groups[0]) == 1


def test_two_unrelated_tables_separate_groups():
    items = [
        _make_item("b1", 1, ["A", "B"], [{"A": "x", "B": "y"}]),
        _make_item("b2", 5, ["X", "Y", "Z"], [{"X": "a", "Y": "b", "Z": "c"}]),
    ]
    groups = group_continuations(items)
    assert len(groups) == 2


def test_continuation_same_headers_adjacent_pages():
    headers = ["Node", "IP", "Status"]
    items = [
        _make_item("b1", 3, headers, [{"Node": "r1", "IP": "10.0.0.1", "Status": "up"}]),
        _make_item("b2", 4, headers, [{"Node": "r2", "IP": "10.0.0.2", "Status": "down"}]),
    ]
    groups = group_continuations(items)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_no_continuation_different_docs():
    headers = ["A", "B"]
    items = [
        _make_item("b1", 1, headers, [{"A": "x", "B": "y"}], doc_id="doc1"),
        _make_item("b2", 2, headers, [{"A": "a", "B": "b"}], doc_id="doc2"),
    ]
    groups = group_continuations(items)
    assert len(groups) == 2


def test_no_continuation_page_gap_too_large():
    headers = ["A", "B"]
    items = [
        _make_item("b1", 1, headers, [{"A": "x", "B": "y"}]),
        _make_item("b2", 4, headers, [{"A": "a", "B": "b"}]),
    ]
    groups = group_continuations(items)
    assert len(groups) == 2


def test_repeated_header_stripped_from_continuation():
    headers = ["Node", "IP"]
    repeated_row = {"Node": "Node", "IP": "IP"}  # header repeated as data row
    items = [
        _make_item("b1", 1, headers, [{"Node": "r1", "IP": "10.0.0.1"}]),
        _make_item("b2", 2, headers, [repeated_row, {"Node": "r2", "IP": "10.0.0.2"}]),
    ]
    groups = group_continuations(items)
    assert len(groups) == 1
    # repeated header row stripped from page 2
    page2_data = groups[0][1]["structured"]
    assert page2_data[0]["Node"] != "Node"


def test_empty_input():
    assert group_continuations([]) == []
