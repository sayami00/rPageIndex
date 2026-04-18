"""Dispatcher tests — patches parsers at dispatcher module level."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.ingestion.dispatcher import dispatch_file
from src.models.ingestion import RawBlock


def _fake_block(fmt: str, page: int = 1, text: str = "Hello world test content here with enough characters to exceed the minimum threshold.") -> RawBlock:
    return RawBlock(
        block_id=f"abc_{fmt}_p0001_s0000",
        doc_id="abc",
        source_file=f"/fake/file.{fmt}",
        source_format=fmt,
        page_number=page,
        sequence=0,
        raw_text=text,
        block_type_hint="paragraph",
    )


def test_dispatch_pdf(tmp_path):
    path = str(tmp_path / "doc.pdf")
    Path(path).write_bytes(b"%PDF fake")
    with patch("src.ingestion.dispatcher.PDFParser") as MockPDF:
        instance = MagicMock()
        instance.safe_parse.return_value = [_fake_block("pdf")]
        MockPDF.return_value = instance
        result = dispatch_file(path)
    instance.safe_parse.assert_called_once_with(path)
    assert result == [_fake_block("pdf")]


def test_dispatch_docx(tmp_path):
    path = str(tmp_path / "doc.docx")
    Path(path).write_bytes(b"fake docx")
    with patch("src.ingestion.dispatcher.DOCXParser") as MockDOCX:
        instance = MagicMock()
        instance.safe_parse.return_value = [_fake_block("docx")]
        MockDOCX.return_value = instance
        result = dispatch_file(path)
    instance.safe_parse.assert_called_once_with(path)


def test_dispatch_xlsx(tmp_path):
    path = str(tmp_path / "doc.xlsx")
    Path(path).write_bytes(b"fake xlsx")
    with patch("src.ingestion.dispatcher.XLSXParser") as MockXLSX:
        instance = MagicMock()
        instance.safe_parse.return_value = [_fake_block("xlsx")]
        MockXLSX.return_value = instance
        result = dispatch_file(path)
    instance.safe_parse.assert_called_once_with(path)


def test_dispatch_html(tmp_path):
    path = str(tmp_path / "doc.html")
    Path(path).write_text("<html><body><p>Hello</p></body></html>")
    with patch("src.ingestion.dispatcher.HTMLParser") as MockHTML:
        instance = MagicMock()
        instance.safe_parse.return_value = [_fake_block("html")]
        MockHTML.return_value = instance
        result = dispatch_file(path)
    instance.safe_parse.assert_called_once_with(path)


def test_dispatch_unknown_extension(tmp_path):
    path = str(tmp_path / "doc.xyz")
    Path(path).write_bytes(b"unknown")
    result = dispatch_file(path)
    assert result == []


def test_dispatch_never_raises():
    result = dispatch_file("/nonexistent/path/to/file.pdf")
    assert isinstance(result, list)


def test_dispatch_ocr_fallback(tmp_path):
    """PDF with no text (empty blocks) triggers OCR fallback."""
    path = str(tmp_path / "scanned.pdf")
    Path(path).write_bytes(b"%PDF fake")
    with patch("src.ingestion.dispatcher.PDFParser") as MockPDF, \
         patch("src.ingestion.dispatcher.OCRParser") as MockOCR:
        pdf_instance = MagicMock()
        pdf_instance.safe_parse.return_value = []

        ocr_instance = MagicMock()
        ocr_block = _fake_block("ocr")
        ocr_instance.safe_parse.return_value = [ocr_block]

        MockPDF.return_value = pdf_instance
        MockOCR.return_value = ocr_instance

        result = dispatch_file(path)

    ocr_instance.safe_parse.assert_called_once_with(path)
    assert result == [ocr_block]
