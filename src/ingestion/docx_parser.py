from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.base import BaseParser, derive_doc_id, generate_block_id
from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)

_STYLE_MAP: dict[str, str] = {
    "heading 1": "heading_1",
    "heading 2": "heading_2",
    "heading 3": "heading_3",
    "heading 4": "heading_3",
    "heading 5": "heading_3",
    "heading 6": "heading_3",
    "list paragraph": "list_item",
    "list bullet": "list_item",
    "list number": "list_item",
    "list bullet 2": "list_item",
    "list bullet 3": "list_item",
    "list number 2": "list_item",
    "list number 3": "list_item",
}


def _style_to_hint(style_name: str | None) -> str:
    if not style_name:
        return "paragraph"
    lower = style_name.lower()
    if lower in _STYLE_MAP:
        return _STYLE_MAP[lower]
    if "heading" in lower:
        return "heading_3"
    if "list" in lower:
        return "list_item"
    return "paragraph"


def _has_page_break(para) -> bool:
    from docx.oxml.ns import qn
    for run in para.runs:
        for br in run._element.findall(f".//{qn('w:br')}"):
            br_type = br.get(f"{{{br.nsmap.get('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')}}}type")
            if br_type == "page":
                return True
    return False


class DOCXParser(BaseParser):
    def parse(self, path: str) -> list[RawBlock]:
        import docx
        from docx.oxml.ns import qn

        doc_id = derive_doc_id(path)
        source_file = str(Path(path).resolve())
        blocks: list[RawBlock] = []

        doc = docx.Document(path)

        current_page = 1
        page_has_heading1 = False
        seq = 0

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                para = _element_to_para(doc, element)
                if para is None:
                    continue

                text = para.text.strip()
                hint = _style_to_hint(para.style.name if para.style else None)

                if hint == "heading_1":
                    if page_has_heading1:
                        current_page += 1
                        seq = 0
                    page_has_heading1 = True
                elif _has_page_break(para):
                    current_page += 1
                    seq = 0

                if not text:
                    continue

                blocks.append(RawBlock(
                    block_id=generate_block_id(doc_id, current_page, seq),
                    doc_id=doc_id,
                    source_file=source_file,
                    source_format="docx",
                    page_number=current_page,
                    sequence=seq,
                    raw_text=text,
                    block_type_hint=hint,
                ))
                seq += 1

            elif tag == "tbl":
                try:
                    table_block = _extract_table(doc, element, doc_id, source_file, current_page, seq)
                    if table_block:
                        blocks.append(table_block)
                        seq += 1
                except Exception as exc:
                    logger.warning("DOCX %s table extraction failed: %s", path, exc)

        return blocks


def _element_to_para(doc, element):
    from docx.text.paragraph import Paragraph
    try:
        return Paragraph(element, doc)
    except Exception:
        return None


def _extract_table(doc, element, doc_id: str, source_file: str, page_num: int, seq: int) -> RawBlock | None:
    from docx.table import Table
    try:
        table = Table(element, doc)
    except Exception:
        return None

    if not table.rows:
        logger.warning("DOCX table has no rows, skipping")
        return None

    headers = [cell.text.strip() for cell in table.rows[0].cells]
    rows = []
    for row in table.rows[1:]:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(dict(zip(headers, cells)))

    raw_text = " | ".join(headers)
    for row in rows:
        raw_text += "\n" + " | ".join(str(v) for v in row.values())

    if not raw_text.strip():
        return None

    return RawBlock(
        block_id=generate_block_id(doc_id, page_num, seq),
        doc_id=doc_id,
        source_file=source_file,
        source_format="docx",
        page_number=page_num,
        sequence=seq,
        raw_text=raw_text,
        block_type_hint="table",
        raw_headers=headers if any(headers) else None,
        raw_rows=rows if rows else None,
    )
