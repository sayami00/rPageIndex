from __future__ import annotations

from rapidfuzz import fuzz

_HEADER_SIMILARITY_THRESHOLD = 85.0
_MAX_PAGE_GAP = 1  # continuation only if pages are adjacent


def group_continuations(table_data: list[dict]) -> list[list[dict]]:
    """Group table_data items that are multi-page continuations of each other.

    Each item is a dict with keys: block, headers, structured.
    Items must be sorted by (doc_id, page_number) before calling.

    Returns list of groups; each group is one logical table across pages.
    """
    if not table_data:
        return []

    groups: list[list[dict]] = [[table_data[0]]]

    for item in table_data[1:]:
        last_group = groups[-1]
        last_item = last_group[-1]

        if _is_continuation(last_item, item):
            # Strip repeated header row from this page before appending
            item = _strip_repeated_header(item)
            last_group.append(item)
        else:
            groups.append([item])

    return groups


def _is_continuation(prev: dict, curr: dict) -> bool:
    prev_block = prev["block"]
    curr_block = curr["block"]

    if prev_block.doc_id != curr_block.doc_id:
        return False

    page_gap = curr_block.page_number - prev_block.page_number
    if page_gap < 1 or page_gap > _MAX_PAGE_GAP + 1:
        return False

    prev_headers = prev["headers"]
    curr_headers = curr["headers"]

    if len(prev_headers) != len(curr_headers):
        return False

    # Case 1: headers on both pages are similar (same structure)
    header_sim = fuzz.ratio(
        " ".join(prev_headers).lower(),
        " ".join(curr_headers).lower(),
    )
    if header_sim >= _HEADER_SIMILARITY_THRESHOLD:
        return True

    # Case 2: curr page has different "headers" because its first row IS the header
    # repeated from the previous page (we check structured data)
    if curr["structured"]:
        first_row_vals = [
            str(curr["structured"][0].get(h, "")).strip()
            for h in curr_headers
        ]
        first_row_str = " ".join(first_row_vals).lower()
        prev_header_str = " ".join(prev_headers).lower()
        row_sim = fuzz.ratio(first_row_str, prev_header_str)
        if row_sim >= _HEADER_SIMILARITY_THRESHOLD:
            return True

    return False


def _strip_repeated_header(item: dict) -> dict:
    """Remove first structured row if it duplicates the headers."""
    headers = item["headers"]
    structured = item["structured"]
    if not structured:
        return item

    first_vals = [str(structured[0].get(h, "")).strip().lower() for h in headers]
    header_vals = [h.strip().lower() for h in headers]

    if first_vals == header_vals:
        return {**item, "structured": structured[1:]}
    return item
