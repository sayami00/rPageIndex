import pytest
from src.tables.pipeline import TablePipeline
from src.models.ingestion import Block


def _make_block(
    block_id: str,
    clean_text: str,
    block_type: str = "table",
    gate_status: str = "PASS",
    page: int = 1,
    sequence: int = 0,
    doc_id: str = "doc1",
) -> Block:
    return Block(
        block_id=block_id,
        doc_id=doc_id,
        source_file="test.pdf",
        page_number=page,
        sequence=sequence,
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


TABLE_TEXT = "Node | IP | Status\nr1 | 10.0.0.1 | active\nr2 | 10.0.0.2 | inactive"


@pytest.fixture
def pipeline():
    return TablePipeline()


def test_basic_table_produces_output(pipeline):
    blocks = [_make_block("b1", TABLE_TEXT)]
    outputs = pipeline.run(blocks)
    assert len(outputs) == 1
    out = outputs[0]
    assert out.table_id == "b1"
    assert out.headers == ["Node", "IP", "Status"]
    assert len(out.structured) == 2
    assert len(out.search_rows) == 2


def test_search_rows_contain_all_headers(pipeline):
    blocks = [_make_block("b1", TABLE_TEXT)]
    outputs = pipeline.run(blocks)
    for row_sentence in outputs[0].search_rows:
        for header in outputs[0].headers:
            assert header in row_sentence, f"'{header}' missing from: {row_sentence!r}"


def test_non_table_blocks_ignored(pipeline):
    blocks = [_make_block("b1", "Some paragraph text", block_type="paragraph")]
    outputs = pipeline.run(blocks)
    assert len(outputs) == 0


def test_rejected_table_ignored(pipeline):
    blocks = [_make_block("b1", TABLE_TEXT, gate_status="REJECT")]
    outputs = pipeline.run(blocks)
    assert len(outputs) == 0


def test_pseudo_table_ignored(pipeline):
    blocks = [_make_block("b1", "Just a list item without pipe separators")]
    outputs = pipeline.run(blocks)
    assert len(outputs) == 0


def test_multi_page_table_merged(pipeline):
    headers_line = "Node | IP | Status"
    page1 = f"{headers_line}\nr1 | 10.0.0.1 | up\nr2 | 10.0.0.2 | up"
    page2 = f"{headers_line}\nr3 | 10.0.0.3 | down\nr4 | 10.0.0.4 | down"
    blocks = [
        _make_block("b1", page1, page=3, sequence=0),
        _make_block("b2", page2, page=4, sequence=0),
    ]
    outputs = pipeline.run(blocks)
    assert len(outputs) == 1
    out = outputs[0]
    assert out.source_pages == [3, 4]
    assert len(out.structured) == 4  # 2 rows from each page


def test_empty_input(pipeline):
    assert pipeline.run([]) == []


def test_source_pages_correct(pipeline):
    blocks = [_make_block("b1", TABLE_TEXT, page=7)]
    outputs = pipeline.run(blocks)
    assert outputs[0].source_pages == [7]


def test_structured_values_correct(pipeline):
    blocks = [_make_block("b1", TABLE_TEXT)]
    outputs = pipeline.run(blocks)
    structured = outputs[0].structured
    nodes = [r["Node"] for r in structured]
    assert "r1" in nodes
    assert "r2" in nodes
