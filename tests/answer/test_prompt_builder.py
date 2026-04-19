from __future__ import annotations

import pytest

from src.answer.prompt_builder import (
    SYSTEM_PROMPT,
    _TYPE_INSTRUCTIONS,
    build_answer_prompt,
    format_context_page,
)
from src.models.index import PageRecord
from src.models.query import Evidence


def _make_page(
    page_number: int,
    body: str = "body text",
    table: str = "",
    heading: str = "Heading",
    section_path: str = "chapter 1",
    source_file: str = "doc.pdf",
    truncated: bool = False,
) -> PageRecord:
    search = f"{heading} {body} {table}".strip()
    return PageRecord(
        page_id=f"doc::p{page_number}",
        doc_id="doc",
        source_file=source_file,
        page_number=page_number,
        heading_text=heading,
        body_text=body,
        table_text=table,
        page_search_text=search,
        section_path=section_path,
        quality_floor=1.0,
        has_low_confidence=False,
        truncated=truncated,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_evidence(pages: list[PageRecord], query_type: str = "page_lookup") -> Evidence:
    total = sum(len(p.body_text) // 4 + 1 for p in pages)
    return Evidence(
        pages=pages,
        total_tokens=total,
        token_budget=3000,
        token_budget_hit=False,
        pages_dropped=0,
        query_type=query_type,
    )


# ── format_context_page ───────────────────────────────────────────────────────

def test_format_includes_page_number() -> None:
    page = _make_page(7)
    result = format_context_page(page)
    assert "Page 7" in result


def test_format_includes_section_path() -> None:
    page = _make_page(3, section_path="chapter 3 / caching")
    result = format_context_page(page)
    assert "chapter 3 / caching" in result


def test_format_includes_filename_only() -> None:
    page = _make_page(1, source_file="/some/path/report.pdf")
    result = format_context_page(page)
    assert "report.pdf" in result
    assert "/some/path/" not in result


def test_format_includes_body_text() -> None:
    page = _make_page(1, body="Cache stores temporary data.")
    result = format_context_page(page)
    assert "Cache stores temporary data." in result


def test_format_includes_table_text() -> None:
    page = _make_page(1, table="web01 | L1 | 4GB")
    result = format_context_page(page)
    assert "web01 | L1 | 4GB" in result


def test_format_truncated_marker() -> None:
    page = _make_page(2, truncated=True)
    result = format_context_page(page)
    assert "[TRUNCATED]" in result


def test_format_no_truncated_marker_when_not_truncated() -> None:
    page = _make_page(2, truncated=False)
    assert "[TRUNCATED]" not in format_context_page(page)


def test_format_missing_section_path_uses_no_section() -> None:
    page = _make_page(1, section_path=None)
    result = format_context_page(page)
    assert "no section" in result


# ── build_answer_prompt ───────────────────────────────────────────────────────

def test_prompt_contains_system_prompt() -> None:
    ev = _make_evidence([_make_page(1)])
    prompt = build_answer_prompt("What is caching?", "page_lookup", ev)
    assert "document assistant" in prompt
    assert "CITATIONS" in prompt


def test_prompt_contains_query() -> None:
    ev = _make_evidence([_make_page(1)])
    prompt = build_answer_prompt("What is the retry policy?", "page_lookup", ev)
    assert "What is the retry policy?" in prompt


def test_prompt_contains_all_evidence_pages() -> None:
    pages = [_make_page(i) for i in range(1, 4)]
    ev = _make_evidence(pages)
    prompt = build_answer_prompt("query", "page_lookup", ev)
    for i in range(1, 4):
        assert f"Page {i}" in prompt


def test_prompt_type_instruction_page_lookup() -> None:
    ev = _make_evidence([_make_page(1)], query_type="page_lookup")
    prompt = build_answer_prompt("query", "page_lookup", ev)
    assert _TYPE_INSTRUCTIONS["page_lookup"] in prompt


def test_prompt_type_instruction_find_all() -> None:
    ev = _make_evidence([_make_page(1)], query_type="find_all")
    prompt = build_answer_prompt("query", "find_all", ev)
    assert _TYPE_INSTRUCTIONS["find_all"] in prompt


def test_prompt_type_instruction_table_query() -> None:
    ev = _make_evidence([_make_page(1)], query_type="table_query")
    prompt = build_answer_prompt("query", "table_query", ev)
    assert _TYPE_INSTRUCTIONS["table_query"] in prompt


def test_prompt_type_instruction_section_lookup() -> None:
    ev = _make_evidence([_make_page(1)], query_type="section_lookup")
    prompt = build_answer_prompt("query", "section_lookup", ev)
    assert _TYPE_INSTRUCTIONS["section_lookup"] in prompt


def test_system_prompt_contains_not_in_context_phrase() -> None:
    assert "not in the provided documents" in SYSTEM_PROMPT


def test_system_prompt_contains_citations_format() -> None:
    assert "CITATIONS:" in SYSTEM_PROMPT
    assert "{filename}" in SYSTEM_PROMPT
    assert "{page_number}" in SYSTEM_PROMPT
