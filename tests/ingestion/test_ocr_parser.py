"""OCR parser tests — skipped if tesseract or pdf2image not available."""
from __future__ import annotations

import pytest

pytesseract = pytest.importorskip("pytesseract")
pdf2image = pytest.importorskip("pdf2image")
reportlab = pytest.importorskip("reportlab")

from unittest.mock import patch, MagicMock
from src.ingestion.ocr_parser import OCRParser, _ocr_page


def _mock_tesseract_data(texts: list[str], confs: list[int], n_pages: int = 1):
    """Build a fake pytesseract image_to_data result."""
    data = {
        "text": texts,
        "conf": confs,
        "block_num": list(range(1, len(texts) + 1)),
        "par_num": [1] * len(texts),
        "line_num": [1] * len(texts),
        "word_num": list(range(1, len(texts) + 1)),
    }
    return data


@patch("pytesseract.image_to_data")
@patch("pytesseract.get_tesseract_version")
def test_ocr_confidence_range(mock_version, mock_data, tmp_path):
    mock_version.return_value = "5.0"
    mock_data.return_value = _mock_tesseract_data(
        ["Hello", "world", "foo"],
        [85, 90, 70],
    )
    from PIL import Image
    img = Image.new("RGB", (100, 100), color="white")

    blocks = _ocr_page(img, "docid123", "/fake/file.pdf", 1)
    assert len(blocks) > 0
    for b in blocks:
        assert 0.0 <= b.ocr_confidence <= 1.0


@patch("pdf2image.convert_from_path")
@patch("pytesseract.image_to_data")
@patch("pytesseract.get_tesseract_version")
def test_ocr_page_numbers(mock_version, mock_data, mock_convert, tmp_path):
    from PIL import Image
    mock_version.return_value = "5.0"
    mock_data.return_value = _mock_tesseract_data(["Text on page"], [80])
    mock_convert.return_value = [
        Image.new("RGB", (100, 100)),
        Image.new("RGB", (100, 100)),
        Image.new("RGB", (100, 100)),
    ]

    blocks = OCRParser().parse("/fake/doc.pdf")
    page_nums = sorted(set(b.page_number for b in blocks))
    assert page_nums == [1, 2, 3]


@patch("pdf2image.convert_from_path")
@patch("pytesseract.image_to_data")
@patch("pytesseract.get_tesseract_version")
def test_ocr_block_id_unique(mock_version, mock_data, mock_convert, tmp_path):
    from PIL import Image
    mock_version.return_value = "5.0"
    mock_data.return_value = _mock_tesseract_data(
        ["Word1", "Word2", "Word3"], [80, 85, 90]
    )
    mock_convert.return_value = [Image.new("RGB", (100, 100))]

    blocks = OCRParser().parse("/fake/doc.pdf")
    ids = [b.block_id for b in blocks]
    assert len(ids) == len(set(ids))
