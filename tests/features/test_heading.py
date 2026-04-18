import pytest
from src.features.heading import extract_headings
from tests.features.conftest import make_block


def test_extracts_heading_1():
    blocks = [make_block(block_type="heading_1", clean_text="System Overview")]
    result = extract_headings(blocks)
    assert len(result) == 1
    assert result[0].feature_type == "heading"
    assert result[0].value == "System Overview"


def test_extracts_heading_2_and_3():
    blocks = [
        make_block(block_id="b1", block_type="heading_2", clean_text="Section 2"),
        make_block(block_id="b2", block_type="heading_3", clean_text="Subsection 2.1"),
    ]
    result = extract_headings(blocks)
    assert len(result) == 2


def test_skips_paragraph():
    blocks = [make_block(block_type="paragraph", clean_text="Some paragraph text")]
    assert extract_headings(blocks) == []


def test_skips_rejected():
    blocks = [make_block(block_type="heading_1", gate_status="REJECT")]
    assert extract_headings(blocks) == []


def test_keeps_flagged():
    blocks = [make_block(block_type="heading_1", gate_status="FLAG")]
    assert len(extract_headings(blocks)) == 1


def test_record_fields_correct():
    blocks = [make_block(
        block_id="doc_p0003_s0002",
        doc_id="mydoc",
        block_type="heading_1",
        clean_text="Introduction",
        page_number=3,
    )]
    r = extract_headings(blocks)[0]
    assert r.block_id == "doc_p0003_s0002"
    assert r.doc_id == "mydoc"
    assert r.page_number == 3
    assert r.key is None
    assert r.entity_subtype is None


def test_strips_whitespace_from_value():
    blocks = [make_block(block_type="heading_1", clean_text="  Spaced Heading  ")]
    assert extract_headings(blocks)[0].value == "Spaced Heading"
