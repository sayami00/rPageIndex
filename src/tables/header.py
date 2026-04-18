from __future__ import annotations

import re

_PIPE_SPLIT = re.compile(r"\s*\|\s*")

# Heuristics to confirm a row is a header
_SHORT_CELL_MAX = 40
_UPPER_RATIO_THRESHOLD = 0.6


def parse_table_text(text: str) -> list[list[str]]:
    """Parse pipe-delimited or tab-delimited clean_text into raw rows.

    Returns list of rows (each row is a list of cell strings).
    Caller determines which row is the header.
    """
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return []

    # Detect delimiter
    use_pipe = any("|" in line for line in lines)

    rows: list[list[str]] = []
    for line in lines:
        if use_pipe:
            cells = [c.strip() for c in _PIPE_SPLIT.split(line)]
        else:
            cells = [c.strip() for c in line.split("\t")]
        rows.append(cells)

    return rows


def detect_header(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    """Identify the header row. Returns (headers, data_rows).

    Strategy:
    1. First row is header if its cells look like labels (short, no numeric-only).
    2. If first row looks like data, generate synthetic headers col_0, col_1, ...
    """
    if not rows:
        return [], []

    n_cols = max(len(r) for r in rows)

    # Normalise column count
    padded = [_pad_row(r, n_cols) for r in rows]

    first = padded[0]

    if _looks_like_header(first):
        headers = [cell if cell else f"col_{i}" for i, cell in enumerate(first)]
        data_rows = padded[1:]
    else:
        headers = [f"col_{i}" for i in range(n_cols)]
        data_rows = padded

    return headers, data_rows


def _pad_row(row: list[str], n: int) -> list[str]:
    if len(row) >= n:
        return row[:n]
    return row + [""] * (n - len(row))


def _looks_like_header(row: list[str]) -> bool:
    if not row:
        return False
    non_empty = [c for c in row if c]
    if not non_empty:
        return False

    # If most cells are short and non-numeric → likely header
    short = sum(1 for c in non_empty if len(c) <= _SHORT_CELL_MAX)
    numeric = sum(1 for c in non_empty if _is_numeric(c))

    short_ratio = short / len(non_empty)
    numeric_ratio = numeric / len(non_empty)

    # Header: mostly short cells, few pure-numeric cells
    return short_ratio >= 0.7 and numeric_ratio <= 0.3


def _is_numeric(val: str) -> bool:
    try:
        float(val.replace(",", ""))
        return True
    except ValueError:
        return False
