from __future__ import annotations


def normalize_table_rows(rows: list[dict]) -> list[dict]:
    """Strip cell whitespace. Drop rows where every cell is empty."""
    cleaned = []
    for row in rows:
        stripped = {
            k: (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
        }
        if any(bool(v) for v in stripped.values()):
            cleaned.append(stripped)
    return cleaned


def normalize_headers(headers: list[str]) -> list[str]:
    return [h.strip() for h in headers]
