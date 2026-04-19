from __future__ import annotations

import re

_CITATIONS_HEADER_RE = re.compile(r"^CITATIONS\s*:", re.IGNORECASE | re.MULTILINE)
_CITATION_LINE_RE = re.compile(r"\[file:\s*(.+?),\s*page:\s*(\d+)\]")


def parse_citations(raw_response: str) -> list[str]:
    """
    Find the CITATIONS: section and return all matching citation strings.
    Returns [] if no CITATIONS block or no valid citation lines found.
    """
    m = _CITATIONS_HEADER_RE.search(raw_response)
    if not m:
        return []
    citations_section = raw_response[m.end():]
    return [
        f"[file: {m.group(1).strip()}, page: {m.group(2)}]"
        for m in _CITATION_LINE_RE.finditer(citations_section)
    ]


def split_answer_body(raw_response: str) -> str:
    """
    Return prose answer — everything before 'CITATIONS:' (stripped).
    Returns full response if no CITATIONS block present.
    """
    m = _CITATIONS_HEADER_RE.search(raw_response)
    if not m:
        return raw_response.strip()
    return raw_response[: m.start()].strip()
