from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.base import BaseParser, derive_doc_id, generate_block_id
from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)

_NOISE_TAGS = ["nav", "header", "footer", "aside", "script", "style"]
_NOISE_CLASS_KEYWORDS = ["sidebar", "nav", "ad", "advertisement", "menu", "breadcrumb"]
_NOISE_ID_KEYWORDS = ["nav", "sidebar", "menu", "header", "footer"]

_HEADING_MAP = {
    "h1": "heading_1",
    "h2": "heading_2",
    "h3": "heading_3",
    "h4": "heading_3",
    "h5": "heading_3",
    "h6": "heading_3",
}


class HTMLParser(BaseParser):
    def parse(self, path: str) -> list[RawBlock]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("beautifulsoup4 not installed")
            return []

        doc_id = derive_doc_id(path)
        source_file = str(Path(path).resolve())

        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.error("HTML %s read failed: %s", path, exc)
            return []

        try:
            bs_parser = "lxml"
            soup = BeautifulSoup(content, bs_parser)
        except Exception:
            soup = BeautifulSoup(content, "html.parser")

        _strip_noise(soup)

        sections = _split_into_sections(soup)
        blocks: list[RawBlock] = []

        for page_num, section in enumerate(sections, start=1):
            seq = 0
            for block in _extract_blocks_from_section(section):
                if not block["text"].strip():
                    continue
                rb_kwargs: dict = dict(
                    block_id=generate_block_id(doc_id, page_num, seq),
                    doc_id=doc_id,
                    source_file=source_file,
                    source_format="html",
                    page_number=page_num,
                    sequence=seq,
                    raw_text=block["text"].strip(),
                    block_type_hint=block["hint"],
                )
                if block.get("headers") is not None:
                    rb_kwargs["raw_headers"] = block["headers"]
                    rb_kwargs["raw_rows"] = block["rows"]
                blocks.append(RawBlock(**rb_kwargs))
                seq += 1

        return blocks


def _strip_noise(soup) -> None:
    for tag in _NOISE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    for el in soup.find_all(True):
        classes = " ".join(el.get("class", [])).lower()
        el_id = (el.get("id") or "").lower()
        if any(kw in classes for kw in _NOISE_CLASS_KEYWORDS):
            el.decompose()
        elif any(kw in el_id for kw in _NOISE_ID_KEYWORDS):
            el.decompose()


def _split_into_sections(soup) -> list:
    body = soup.find("body") or soup

    sections = body.find_all("section", recursive=False)
    if sections:
        return sections

    # fallback: split on <hr>
    hrs = body.find_all("hr")
    if hrs:
        parts = []
        current_children = []
        for child in body.children:
            if hasattr(child, "name") and child.name == "hr":
                if current_children:
                    parts.append(current_children)
                current_children = []
            else:
                current_children.append(child)
        if current_children:
            parts.append(current_children)

        class _FakeSection:
            def __init__(self, children):
                self._children = children

            def __iter__(self):
                return iter(self._children)

            @property
            def children(self):
                return self._children

        return [_FakeSection(c) for c in parts if c]

    return [body]


def _extract_blocks_from_section(section) -> list[dict]:
    blocks: list[dict] = []

    children = list(getattr(section, "children", section))

    for el in children:
        if not hasattr(el, "name") or el.name is None:
            text = str(el).strip()
            if text:
                blocks.append({"hint": "paragraph", "text": text})
            continue

        tag = el.name.lower()

        if tag in _HEADING_MAP:
            text = el.get_text(separator=" ", strip=True)
            if text:
                blocks.append({"hint": _HEADING_MAP[tag], "text": text})

        elif tag == "p":
            text = el.get_text(separator=" ", strip=True)
            if text:
                blocks.append({"hint": "paragraph", "text": text})

        elif tag in ("ul", "ol"):
            for li in el.find_all("li", recursive=False):
                text = li.get_text(separator=" ", strip=True)
                if text:
                    blocks.append({"hint": "list_item", "text": text})

        elif tag == "table":
            table_block = _extract_html_table(el)
            if table_block:
                blocks.append(table_block)

        elif tag == "section":
            blocks.extend(_extract_blocks_from_section(el))

    return blocks


def _extract_html_table(el) -> dict | None:
    rows_el = el.find_all("tr")
    if not rows_el:
        return None

    headers: list[str] = []
    first_row = rows_el[0]
    ths = first_row.find_all("th")
    if ths:
        headers = [th.get_text(strip=True) for th in ths]
    else:
        headers = [td.get_text(strip=True) for td in first_row.find_all("td")]

    rows: list[dict] = []
    data_rows = rows_el[1:] if ths else rows_el
    for tr in data_rows:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
        elif cells:
            rows.append({str(i): v for i, v in enumerate(cells)})

    raw_text = " | ".join(headers)
    for row in rows:
        raw_text += "\n" + " | ".join(str(v) for v in row.values())

    if not raw_text.strip():
        return None

    return {
        "hint": "table",
        "text": raw_text,
        "headers": headers if any(headers) else None,
        "rows": rows,
    }
