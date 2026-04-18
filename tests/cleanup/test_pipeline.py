import pytest
from src.cleanup.pipeline import CleanupPipeline
from src.models.ingestion import RawBlock


def _raw(
    block_id: str,
    raw_text: str,
    block_type_hint: str = "paragraph",
    source_format: str = "pdf",
    page_number: int = 1,
    sequence: int = 0,
    ocr_confidence: float | None = None,
) -> RawBlock:
    return RawBlock(
        block_id=block_id,
        doc_id="testdoc",
        source_file="test.pdf",
        source_format=source_format,
        page_number=page_number,
        sequence=sequence,
        raw_text=raw_text,
        block_type_hint=block_type_hint,
        ocr_confidence=ocr_confidence,
    )


@pytest.fixture
def pipeline():
    return CleanupPipeline()


def test_clean_block_produces_block(pipeline):
    blocks = [_raw("b1", "This is a clean paragraph with enough text to pass quality gate.")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    b = result[0]
    assert b.block_id == "b1"
    assert b.gate_status == "PASS"
    assert b.should_index is True
    assert b.low_confidence is False


def test_too_short_block_dropped(pipeline):
    blocks = [_raw("b1", "hi")]
    result = pipeline.run(blocks)
    assert len(result) == 0


def test_boilerplate_reduces_gate(pipeline):
    blocks = [_raw("b1", "© 2024 All Rights Reserved")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    assert result[0].is_boilerplate is True
    assert result[0].gate_status in ("REJECT", "FLAG")


def test_duplicate_flagged(pipeline):
    text = "This sentence appears twice in the document as a near-exact duplicate copy."
    blocks = [
        _raw("b1", text, sequence=0),
        _raw("b2", text, sequence=1),
    ]
    result = pipeline.run(blocks)
    assert len(result) == 2
    b1 = next(b for b in result if b.block_id == "b1")
    b2 = next(b for b in result if b.block_id == "b2")
    assert b1.is_duplicate is False
    assert b2.is_duplicate is True
    assert b2.duplicate_of == "b1"


def test_table_type_hint_classified_as_table(pipeline):
    blocks = [_raw("b1", "col1 | col2\nval1 | val2\nval3 | val4", block_type_hint="table")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    assert result[0].block_type == "table"


def test_list_item_normalized(pipeline):
    blocks = [_raw("b1", "• Important requirement for the system")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    assert result[0].clean_text.startswith("- ")
    assert result[0].block_type == "list_item"


def test_ocr_text_fixed(pipeline):
    blocks = [_raw("b1", "0pen the 1nterface and select 0ptions", source_format="ocr")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    assert "Open" in result[0].clean_text
    assert "Interface" in result[0].clean_text


def test_search_text_is_lowercase(pipeline):
    blocks = [_raw("b1", "System Architecture Overview and Requirements")]
    result = pipeline.run(blocks)
    assert len(result) == 1
    assert result[0].search_text == result[0].search_text.lower()


def test_gate_status_consistent_with_should_index(pipeline):
    blocks = [
        _raw("b1", "Clean paragraph with sufficient content for indexing.", sequence=0),
        _raw("b2", "Another solid paragraph with good quality text.", sequence=1),
    ]
    result = pipeline.run(blocks)
    for b in result:
        if b.gate_status == "REJECT":
            assert b.should_index is False
        else:
            assert b.should_index is True
        assert b.low_confidence == (b.gate_status == "FLAG")


def test_empty_input(pipeline):
    assert pipeline.run([]) == []
