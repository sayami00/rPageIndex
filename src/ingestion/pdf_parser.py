from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.base import BaseParser, derive_doc_id, generate_block_id
from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)

_MIN_TEXT_CHARS = 50
_COLUMN_GAP_PX = 100
_LINE_Y_TOLERANCE = 3


def _has_text_layer(path: str) -> bool:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        total = sum(len(p.extract_text() or "") for p in pdf.pages)
    return total >= _MIN_TEXT_CHARS


class PDFParser(BaseParser):
    def parse(self, path: str) -> list[RawBlock]:
        import pdfplumber

        doc_id = derive_doc_id(path)
        source_file = str(Path(path).resolve())
        blocks: list[RawBlock] = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_num = page.page_number  # 1-indexed

                page_text = page.extract_text() or ""
                if len(page_text) < 10:
                    logger.debug("PDF page %d has no text layer, skipping (OCR needed)", page_num)
                    continue

                try:
                    page_blocks = _extract_page_blocks(page, doc_id, source_file, page_num)
                    blocks.extend(page_blocks)
                except Exception as exc:
                    logger.warning("PDF %s page %d extraction failed: %s", path, page_num, exc)

        return blocks


def _extract_page_blocks(page, doc_id: str, source_file: str, page_num: int) -> list[RawBlock]:
    import pdfplumber

    blocks: list[RawBlock] = []

    tables = page.extract_tables() or []
    table_bboxes = [t.bbox for t in page.find_tables()] if tables else []

    words = page.extract_words() or []
    text_lines = _group_words_into_lines(words, table_bboxes)
    text_columns = _detect_columns(text_lines, page.width)

    # Collect (y_position, block_dict) for ordering
    items: list[tuple[float, dict]] = []

    seq = 0
    for col_lines in text_columns:
        merged_paragraphs = _merge_lines_to_paragraphs(col_lines)
        for para_y, para_text in merged_paragraphs:
            if not para_text.strip():
                continue
            items.append((para_y, {
                "type": "text",
                "text": para_text,
                "y": para_y,
            }))

    for i, (table_data, bbox) in enumerate(zip(tables, table_bboxes)):
        if not table_data or not table_data[0]:
            continue
        table_y = bbox[1] if bbox else 0.0
        items.append((table_y, {
            "type": "table",
            "data": table_data,
            "y": table_y,
        }))

    items.sort(key=lambda x: x[0])

    for _, item in items:
        block_id = generate_block_id(doc_id, page_num, seq)
        if item["type"] == "text":
            blocks.append(RawBlock(
                block_id=block_id,
                doc_id=doc_id,
                source_file=source_file,
                source_format="pdf",
                page_number=page_num,
                sequence=seq,
                raw_text=item["text"].strip(),
                block_type_hint="paragraph",
            ))
        else:
            table_data = item["data"]
            headers = [str(c or "").strip() for c in table_data[0]]
            rows = []
            for row in table_data[1:]:
                rows.append({headers[j]: str(cell or "").strip() for j, cell in enumerate(row)})
            raw_text = " | ".join(headers)
            for row in rows:
                raw_text += "\n" + " | ".join(str(v) for v in row.values())
            if not raw_text.strip():
                seq += 1
                continue
            blocks.append(RawBlock(
                block_id=block_id,
                doc_id=doc_id,
                source_file=source_file,
                source_format="pdf",
                page_number=page_num,
                sequence=seq,
                raw_text=raw_text,
                block_type_hint="table",
                raw_headers=headers if headers else None,
                raw_rows=rows if rows else None,
            ))
        seq += 1

    return blocks


def _group_words_into_lines(words: list[dict], table_bboxes: list) -> list[dict]:
    """Group words into lines by y-position, excluding words inside table bboxes."""
    filtered = []
    for w in words:
        in_table = any(
            bbox[0] <= w["x0"] and w["x1"] <= bbox[2] and bbox[1] <= w["top"] and w["bottom"] <= bbox[3]
            for bbox in table_bboxes
        )
        if not in_table:
            filtered.append(w)

    if not filtered:
        return []

    lines: list[dict] = []
    current_line: list[dict] = [filtered[0]]
    current_y = filtered[0]["top"]

    for w in filtered[1:]:
        if abs(w["top"] - current_y) <= _LINE_Y_TOLERANCE:
            current_line.append(w)
        else:
            lines.append({"words": current_line, "y": current_y})
            current_line = [w]
            current_y = w["top"]
    lines.append({"words": current_line, "y": current_y})
    return lines


def _detect_columns(lines: list[dict], page_width: float) -> list[list[dict]]:
    """Split lines into columns if a significant x-gap exists."""
    if not lines:
        return [[]]

    all_x = [w["x0"] for line in lines for w in line["words"]]
    if not all_x:
        return [lines]

    midpoint = page_width / 2
    left_lines = [l for l in lines if any(w["x0"] < midpoint for w in l["words"])]
    right_lines = [l for l in lines if any(w["x0"] >= midpoint for w in l["words"])]

    # Only split into columns if right column has substantial content
    if len(right_lines) > 2 and len(left_lines) > 2:
        left_x_max = max((w["x1"] for l in left_lines for w in l["words"]), default=0)
        right_x_min = min((w["x0"] for l in right_lines for w in l["words"]), default=page_width)
        if right_x_min - left_x_max > _COLUMN_GAP_PX:
            return [left_lines, right_lines]

    return [lines]


def _merge_lines_to_paragraphs(lines: list[dict]) -> list[tuple[float, str]]:
    """Merge consecutive lines into paragraph blocks."""
    if not lines:
        return []

    paragraphs: list[tuple[float, str]] = []
    current_texts: list[str] = []
    current_y = lines[0]["y"] if lines else 0.0
    prev_y = lines[0]["y"] if lines else 0.0

    for line in lines:
        line_text = " ".join(w["text"] for w in sorted(line["words"], key=lambda w: w["x0"]))
        gap = line["y"] - prev_y

        if gap > 20 and current_texts:
            paragraphs.append((current_y, " ".join(current_texts)))
            current_texts = [line_text]
            current_y = line["y"]
        else:
            current_texts.append(line_text)

        prev_y = line["y"]

    if current_texts:
        paragraphs.append((current_y, " ".join(current_texts)))

    return paragraphs
