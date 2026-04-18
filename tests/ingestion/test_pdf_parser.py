"""PDF parser tests — uses pdfplumber to create in-memory PDFs via reportlab."""
from __future__ import annotations

import io
import pytest

pytest.importorskip("pdfplumber")
reportlab = pytest.importorskip("reportlab")

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from src.ingestion.pdf_parser import PDFParser


def _make_text_pdf(tmp_path, pages: list[str]) -> str:
    path = str(tmp_path / "text.pdf")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter)
    story = []
    for i, text in enumerate(pages):
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.5 * inch))
    doc.build(story)
    return path


def _make_table_pdf(tmp_path) -> str:
    path = str(tmp_path / "table.pdf")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter)
    data = [["Name", "Age", "City"], ["Alice", "30", "NY"], ["Bob", "25", "LA"]]
    story = [Table(data)]
    doc.build(story)
    return path


def test_pdf_text_blocks(tmp_path):
    path = _make_text_pdf(tmp_path, ["Hello world this is page one content."])
    blocks = PDFParser().parse(path)
    assert len(blocks) > 0
    for b in blocks:
        assert b.source_file == path or b.source_file.endswith("text.pdf")
        assert b.page_number >= 1
        assert b.block_id
        assert b.raw_text.strip()
        assert b.source_format == "pdf"


def test_pdf_table_blocks(tmp_path):
    path = _make_table_pdf(tmp_path)
    blocks = PDFParser().parse(path)
    table_blocks = [b for b in blocks if b.block_type_hint == "table"]
    assert len(table_blocks) >= 1
    tb = table_blocks[0]
    assert tb.raw_headers is not None
    assert len(tb.raw_rows) > 0


def test_pdf_no_text_layer_returns_empty(tmp_path):
    """PDFParser returns [] for pages with no text (OCR handled by dispatcher)."""
    from reportlab.platypus import SimpleDocTemplate, Spacer
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch

    path = str(tmp_path / "blank.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter)
    doc.build([Spacer(1, 1 * inch)])

    blocks = PDFParser().parse(path)
    assert blocks == []


def test_pdf_block_ids_unique(tmp_path):
    path = _make_text_pdf(tmp_path, [
        "First page has some content here for testing.",
        "Second page has different content here.",
    ])
    blocks = PDFParser().parse(path)
    ids = [b.block_id for b in blocks]
    assert len(ids) == len(set(ids)), "Duplicate block_ids found"
