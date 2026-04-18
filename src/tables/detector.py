from __future__ import annotations

import re

from src.models.ingestion import Block

_PIPE_RE = re.compile(r"\s\|\s")
_MIN_COLS = 2


def filter_table_blocks(blocks: list[Block]) -> list[Block]:
    """Return non-REJECT table blocks that are genuine tables (not pseudo-tables)."""
    result = []
    for b in blocks:
        if b.block_type != "table":
            continue
        if b.gate_status == "REJECT":
            continue
        if _is_pseudo_table(b.clean_text):
            continue
        result.append(b)
    return result


def _is_pseudo_table(text: str) -> bool:
    """Return True when block looks like a misclassified paragraph.

    Pseudo-table: no pipe separators, no tabs, or fewer than MIN_COLS columns.
    """
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return True

    has_pipe = any(_PIPE_RE.search(line) for line in lines)
    has_tab = any("\t" in line for line in lines)

    if not has_pipe and not has_tab:
        return True

    # Check column count on first data line
    first = lines[0]
    if has_pipe:
        col_count = len(first.split("|"))
    else:
        col_count = len(first.split("\t"))

    return col_count < _MIN_COLS
