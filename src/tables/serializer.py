from __future__ import annotations


def serialize_row(headers: list[str], row: dict) -> str:
    """Convert one table row to a natural language sentence.

    Rules (column-agnostic — no hardcoded names):
    - Every non-empty column: "ColumnName value" (BM25 matches on column token)
    - Numeric, IP, version values: kept exact
    - Empty cells: skipped entirely (no "None", "null", "N/A")
    - Boolean True: column name only
    - Boolean False: omitted
    - Separator: plain space
    """
    parts: list[str] = []
    for col in headers:
        val = row.get(col, "")
        if val is None or val == "":
            continue
        if isinstance(val, bool):
            if val:
                parts.append(col)
            # False → skip
        else:
            parts.append(f"{col} {val}")
    return " ".join(parts)


def serialize_table(headers: list[str], structured: list[dict]) -> list[str]:
    """Serialize all rows. Returns one sentence per row."""
    return [serialize_row(headers, row) for row in structured]
