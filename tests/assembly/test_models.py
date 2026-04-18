import pytest
from src.assembly.models import PageRecord


def test_page_record_defaults():
    r = PageRecord(
        doc_id="doc1",
        source_file="test.pdf",
        page_number=1,
        heading_text="Overview",
        body_text="Some content",
        table_text="",
        page_search_text="Overview Some content",
    )
    assert r.features == []
    assert r.tables == []
    assert r.quality_floor == 1.0
    assert r.block_count == 0


def test_page_record_fields_assigned():
    r = PageRecord(
        doc_id="doc1",
        source_file="doc.pdf",
        page_number=5,
        heading_text="Section 5",
        body_text="Body here",
        table_text="Node r1 IP 10.0.0.1",
        page_search_text="Section 5 Body here Node r1 IP 10.0.0.1",
        quality_floor=0.72,
        block_count=4,
    )
    assert r.page_number == 5
    assert r.quality_floor == 0.72
    assert r.block_count == 4
