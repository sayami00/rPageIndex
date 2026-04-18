import pytest
from src.assembly.pipeline import AssemblyPipeline
from src.models.ingestion import Block
from src.features.models import FeatureRecord
from src.tables.models import TableOutput


def _block(
    block_id: str,
    page: int,
    block_type: str = "paragraph",
    clean_text: str = "Some content on this page.",
    gate_status: str = "PASS",
    doc_id: str = "doc1",
    quality_score: float = 0.8,
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


@pytest.fixture
def pipeline():
    return AssemblyPipeline()


def test_empty_input(pipeline):
    assert pipeline.run([], {}, []) == []


def test_single_page(pipeline):
    blocks = [_block("b1", page=1), _block("b2", page=1)]
    result = pipeline.run(blocks, {}, [])
    assert len(result) == 1
    assert result[0].page_number == 1
    assert result[0].block_count == 2


def test_multiple_pages_produce_separate_records(pipeline):
    blocks = [
        _block("b1", page=1),
        _block("b2", page=2),
        _block("b3", page=3),
    ]
    result = pipeline.run(blocks, {}, [])
    assert len(result) == 3
    pages = [r.page_number for r in result]
    assert pages == [1, 2, 3]


def test_sorted_by_doc_then_page(pipeline):
    blocks = [
        _block("b1", page=3, doc_id="doc1"),
        _block("b2", page=1, doc_id="doc2"),
        _block("b3", page=1, doc_id="doc1"),
    ]
    result = pipeline.run(blocks, {}, [])
    assert len(result) == 3
    assert (result[0].doc_id, result[0].page_number) == ("doc1", 1)
    assert (result[1].doc_id, result[1].page_number) == ("doc1", 3)
    assert (result[2].doc_id, result[2].page_number) == ("doc2", 1)


def test_feature_index_flattened_and_attached(pipeline):
    blocks = [_block("b1", page=2)]
    feature_index = {
        "heading": [
            FeatureRecord("heading", "Chapter 1", "b1", "doc1", 2)
        ],
        "bullet_item": [
            FeatureRecord("bullet_item", "- Point", "b1", "doc1", 2)
        ],
    }
    result = pipeline.run(blocks, feature_index, [])
    assert len(result) == 1
    assert len(result[0].features) == 2


def test_table_attached_to_correct_page(pipeline):
    blocks = [_block("b1", page=5), _block("b2", page=6)]
    tables = [TableOutput(
        table_id="t1", doc_id="doc1",
        source_pages=[5, 6], headers=["A"],
        structured=[{"A": "v"}], search_rows=["A v"],
    )]
    result = pipeline.run(blocks, {}, tables)
    page5 = next(r for r in result if r.page_number == 5)
    page6 = next(r for r in result if r.page_number == 6)
    assert len(page5.tables) == 1
    assert len(page6.tables) == 1


def test_heading_and_body_text_populated(pipeline):
    blocks = [
        _block("b1", page=1, block_type="heading_1", clean_text="Main Heading"),
        _block("b2", page=1, block_type="paragraph", clean_text="Body paragraph text"),
    ]
    result = pipeline.run(blocks, {}, [])
    r = result[0]
    assert "Main Heading" in r.heading_text
    assert "Body paragraph text" in r.body_text
    assert "Main Heading" in r.page_search_text
    assert "Body paragraph text" in r.page_search_text


def test_multi_doc_no_cross_contamination(pipeline):
    blocks = [
        _block("b1", page=1, doc_id="doc1", clean_text="Document one content"),
        _block("b2", page=1, doc_id="doc2", clean_text="Document two content"),
    ]
    result = pipeline.run(blocks, {}, [])
    doc1_rec = next(r for r in result if r.doc_id == "doc1")
    doc2_rec = next(r for r in result if r.doc_id == "doc2")
    assert "Document two content" not in doc1_rec.body_text
    assert "Document one content" not in doc2_rec.body_text


def test_quality_floor_matches_minimum(pipeline):
    blocks = [
        _block("b1", page=1, quality_score=0.9),
        _block("b2", page=1, quality_score=0.42),
        _block("b3", page=1, quality_score=0.75),
    ]
    result = pipeline.run(blocks, {}, [])
    assert result[0].quality_floor == pytest.approx(0.42)


def test_reject_blocks_excluded_from_body(pipeline):
    blocks = [
        _block("b1", page=1, clean_text="Good content", gate_status="PASS"),
        _block("b2", page=1, clean_text="Garbage content", gate_status="REJECT"),
    ]
    result = pipeline.run(blocks, {}, [])
    assert "Good content" in result[0].body_text
    assert "Garbage content" not in result[0].body_text
