from __future__ import annotations

import logging
from pathlib import Path

from src.ingestion.base import BaseParser, derive_doc_id, generate_block_id
from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)


class XLSXParser(BaseParser):
    def parse(self, path: str) -> list[RawBlock]:
        import pandas as pd

        doc_id = derive_doc_id(path)
        source_file = str(Path(path).resolve())
        suffix = Path(path).suffix.lower()
        blocks: list[RawBlock] = []

        if suffix == ".csv":
            sheets = {"sheet1": pd.read_csv(path, dtype=str, keep_default_na=False)}
        else:
            sheets = pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)

        for page_num, (sheet_name, df) in enumerate(sheets.items(), start=1):
            try:
                block = _sheet_to_block(df, sheet_name, doc_id, source_file, page_num)
                if block:
                    blocks.append(block)
            except Exception as exc:
                logger.warning("XLSX %s sheet '%s' failed: %s", path, sheet_name, exc)

        return blocks


def _sheet_to_block(df, sheet_name: str, doc_id: str, source_file: str, page_num: int) -> RawBlock | None:
    import pandas as pd

    if df.empty or df.shape[0] == 0:
        logger.warning("Sheet '%s' is empty, skipping", sheet_name)
        return None

    df = df.fillna("")

    headers = [str(c) for c in df.columns.tolist()]
    rows = [dict(zip(headers, (str(v) for v in row))) for row in df.itertuples(index=False, name=None)]

    all_empty = all(all(v == "" for v in row.values()) for row in rows)
    if all_empty:
        logger.warning("Sheet '%s' has all empty rows, skipping", sheet_name)
        return None

    raw_text = " | ".join(headers)
    for row in rows:
        row_str = " | ".join(str(v) for v in row.values())
        if row_str.replace("|", "").strip():
            raw_text += "\n" + row_str

    all_str = all(not _has_numeric(df[c]) for c in df.columns)
    hint = "boilerplate" if (all_str and df.shape[0] < 3) else "table"

    return RawBlock(
        block_id=generate_block_id(doc_id, page_num, 0),
        doc_id=doc_id,
        source_file=source_file,
        source_format="xlsx",
        page_number=page_num,
        sequence=0,
        raw_text=raw_text,
        block_type_hint=hint,
        raw_headers=headers,
        raw_rows=rows,
    )


def _has_numeric(series) -> bool:
    for v in series:
        try:
            float(str(v))
            return True
        except ValueError:
            pass
    return False
