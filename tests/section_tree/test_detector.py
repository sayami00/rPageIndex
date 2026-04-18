import pytest
from src.section_tree.detector import extract_headings, HEADING_TYPES
from tests.section_tree.conftest import make_block


def test_returns_only_headings():
    blocks = [
        make_block("b1", "paragraph", "body", sequence=0),
        make_block("b2", "heading_1", "Title", sequence=1),
        make_block("b3", "table", "| A |", sequence=2),
        make_block("b4", "heading_2", "Sub", sequence=3),
    ]
    result = extract_headings(blocks)
    assert len(result) == 2
    assert all(b.block_type in HEADING_TYPES for b in result)


def test_sorted_by_sequence():
    blocks = [
        make_block("b1", "heading_2", "Sub", sequence=10),
        make_block("b2", "heading_1", "Title", sequence=3),
        make_block("b3", "heading_3", "Deep", sequence=7),
    ]
    result = extract_headings(blocks)
    seqs = [b.sequence for b in result]
    assert seqs == sorted(seqs)


def test_all_gate_statuses_included():
    blocks = [
        make_block("b1", "heading_1", "Pass", sequence=0, gate_status="PASS"),
        make_block("b2", "heading_2", "Flag", sequence=1, gate_status="FLAG"),
        make_block("b3", "heading_3", "Reject", sequence=2, gate_status="REJECT"),
    ]
    result = extract_headings(blocks)
    assert len(result) == 3


def test_empty_input():
    assert extract_headings([]) == []


def test_no_headings_in_blocks():
    blocks = [
        make_block("b1", "paragraph", "text"),
        make_block("b2", "table", "| x |"),
    ]
    assert extract_headings(blocks) == []
