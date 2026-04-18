import pytest
from src.assembly.assembler import build_page_record
from src.models.ingestion import Block
from src.features.models import FeatureRecord
from src.tables.models import TableOutput


def _block(
    block_id: str,
    block_type: str,
    clean_text: str,
    gate_status: str = "PASS",
    quality_score: float = 0.8,
    page: int = 3,
    doc_id: str = "doc1",
) -> Block:
    return Block(
        block_id=block_id,
        doc_id=doc_id,
        source_file="test.pdf",
        page_number=page,
        sequence=0,
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


def _feature(page: int = 3, doc_id: str = "doc1") -> FeatureRecord:
    return FeatureRecord(
        feature_type="heading",
        value="Test Heading",
        block_id="b1",
        doc_id=doc_id,
        page_number=page,
    )


def _table(source_pages: list[int], doc_id: str = "doc1") -> TableOutput:
    return TableOutput(
        table_id="t1",
        doc_id=doc_id,
        source_pages=source_pages,
        headers=["Node", "IP"],
        structured=[{"Node": "r1", "IP": "10.0.0.1"}],
        search_rows=["Node r1 IP 10.0.0.1"],
    )


def test_heading_text_contains_all_headings():
    blocks = [
        _block("b1", "heading_1", "System Overview"),
        _block("b2", "heading_2", "Network Config"),
        _block("b3", "paragraph", "Some paragraph"),
    ]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "System Overview" in r.heading_text
    assert "Network Config" in r.heading_text
    assert "Some paragraph" not in r.heading_text


def test_heading_text_includes_flagged_headings():
    blocks = [_block("b1", "heading_1", "Flagged Header", gate_status="FLAG")]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "Flagged Header" in r.heading_text


def test_body_text_includes_pass_paragraphs():
    blocks = [_block("b1", "paragraph", "Good paragraph text")]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "Good paragraph text" in r.body_text


def test_body_text_includes_flagged_paragraphs():
    blocks = [_block("b1", "paragraph", "Flagged paragraph", gate_status="FLAG")]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "Flagged paragraph" in r.body_text


def test_body_text_excludes_rejected_paragraphs():
    blocks = [
        _block("b1", "paragraph", "Good text"),
        _block("b2", "paragraph", "Rejected text", gate_status="REJECT"),
    ]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "Good text" in r.body_text
    assert "Rejected text" not in r.body_text


def test_table_text_contains_search_rows():
    tables = [_table(source_pages=[3])]
    r = build_page_record("doc1", "test.pdf", 3, [], [], tables)
    assert "Node r1 IP 10.0.0.1" in r.table_text


def test_table_text_excludes_other_pages():
    tables = [_table(source_pages=[5, 6])]
    r = build_page_record("doc1", "test.pdf", 3, [], [], tables)
    assert r.table_text == ""


def test_table_text_multi_page_table_included_on_all_pages():
    tables = [_table(source_pages=[3, 4])]
    r3 = build_page_record("doc1", "test.pdf", 3, [], [], tables)
    r4 = build_page_record("doc1", "test.pdf", 4, [], [], tables)
    assert "Node r1" in r3.table_text
    assert "Node r1" in r4.table_text


def test_table_text_excludes_other_docs():
    tables = [_table(source_pages=[3], doc_id="doc2")]
    r = build_page_record("doc1", "test.pdf", 3, [], [], tables)
    assert r.table_text == ""


def test_page_search_text_combines_all():
    blocks = [
        _block("b1", "heading_1", "Overview"),
        _block("b2", "paragraph", "Body content"),
    ]
    tables = [_table(source_pages=[3])]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], tables)
    assert "Overview" in r.page_search_text
    assert "Body content" in r.page_search_text
    assert "Node r1" in r.page_search_text


def test_page_search_text_no_double_spaces():
    blocks = [_block("b1", "paragraph", "clean text")]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert "  " not in r.page_search_text


def test_features_filtered_to_page_and_doc():
    features = [
        _feature(page=3, doc_id="doc1"),
        _feature(page=4, doc_id="doc1"),   # wrong page
        _feature(page=3, doc_id="doc2"),   # wrong doc
    ]
    r = build_page_record("doc1", "test.pdf", 3, [], features, [])
    assert len(r.features) == 1
    assert r.features[0].page_number == 3


def test_tables_filtered_to_page_and_doc():
    tables = [
        _table(source_pages=[3], doc_id="doc1"),
        _table(source_pages=[5], doc_id="doc1"),   # wrong page
        _table(source_pages=[3], doc_id="doc2"),   # wrong doc
    ]
    r = build_page_record("doc1", "test.pdf", 3, [], [], tables)
    assert len(r.tables) == 1


def test_quality_floor_is_minimum():
    blocks = [
        _block("b1", "paragraph", "text", quality_score=0.9),
        _block("b2", "paragraph", "text", quality_score=0.45),
        _block("b3", "heading_1", "text", quality_score=0.75),
    ]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert r.quality_floor == 0.45


def test_quality_floor_empty_blocks():
    r = build_page_record("doc1", "test.pdf", 3, [], [], [])
    assert r.quality_floor == 0.0


def test_block_count():
    blocks = [_block(f"b{i}", "paragraph", "text") for i in range(5)]
    r = build_page_record("doc1", "test.pdf", 3, blocks, [], [])
    assert r.block_count == 5
