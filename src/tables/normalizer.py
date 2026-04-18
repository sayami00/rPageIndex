from __future__ import annotations


def normalize_rows(headers: list[str], data_rows: list[list[str]]) -> list[dict]:
    """Convert raw cell lists to dicts with cleaned values.

    - Strips whitespace from all cells
    - None / empty → empty string
    - Merged cell heuristic: if a cell is empty and its left neighbour is non-empty,
      fill it with the left neighbour value (common PDF merge artifact)
    """
    structured: list[dict] = []
    for raw_row in data_rows:
        row = _normalize_cells(raw_row, len(headers))
        row = _fill_merged_cells(row)
        structured.append(dict(zip(headers, row)))
    return structured


def _normalize_cells(row: list[str], n_cols: int) -> list[str]:
    padded = (row + [""] * n_cols)[:n_cols]
    return [c.strip() if c is not None else "" for c in padded]


def _fill_merged_cells(row: list[str]) -> list[str]:
    result = list(row)
    for i in range(1, len(result)):
        if result[i] == "" and result[i - 1] != "":
            result[i] = result[i - 1]
    return result
