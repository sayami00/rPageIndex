from __future__ import annotations

import logging
from pathlib import Path

from src.models.ingestion import RawBlock
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.docx_parser import DOCXParser
from src.ingestion.xlsx_parser import XLSXParser
from src.ingestion.html_parser import HTMLParser
from src.ingestion.ocr_parser import OCRParser

logger = logging.getLogger(__name__)

_MIN_TEXT_CHARS_FOR_TEXT_LAYER = 50

_EXT_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".csv": "csv",
    ".html": "html",
    ".htm": "html",
}


def dispatch_file(path: str) -> list[RawBlock]:
    try:
        return _dispatch(path)
    except Exception as exc:
        logger.error("dispatch_file failed on %s: %s", path, exc)
        return []


def _dispatch(path: str) -> list[RawBlock]:
    suffix = Path(path).suffix.lower()
    fmt = _EXT_MAP.get(suffix)

    if fmt is None:
        logger.warning("Unknown file extension '%s' for %s, skipping", suffix, path)
        return []

    if fmt == "pdf":
        return _handle_pdf(path)
    if fmt == "docx":
        return DOCXParser().safe_parse(path)
    if fmt in ("xlsx", "csv"):
        return XLSXParser().safe_parse(path)
    if fmt == "html":
        return HTMLParser().safe_parse(path)

    logger.warning("Unhandled format '%s' for %s", fmt, path)
    return []


def _handle_pdf(path: str) -> list[RawBlock]:
    pdf_blocks = PDFParser().safe_parse(path)

    total_chars = sum(len(b.raw_text) for b in pdf_blocks)
    if total_chars < _MIN_TEXT_CHARS_FOR_TEXT_LAYER:
        logger.info("PDF %s has no text layer (total_chars=%d), falling back to OCR", path, total_chars)
        return OCRParser().safe_parse(path)

    return pdf_blocks
