from __future__ import annotations

import math

import pytest

from src.evidence.assembler import (
    MAX_EVIDENCE_TOKENS,
    EvidenceAssembler,
    _CHARS_PER_TOKEN,
    _count_tokens,
    _truncate_page,
)
from src.models.exceptions import EmptyEvidenceError
from src.models.index import PageRecord
from src.models.query import Candidate


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_page(
    page_number: int,
    body: str = "",
    table: str = "",
    heading: str = "Heading",
    section_path: str | None = "chapter 1",
    doc_id: str = "doc",
) -> PageRecord:
    search = f"{heading} {body} {table}".strip()
    return PageRecord(
        page_id=f"{doc_id}::p{page_number}",
        doc_id=doc_id,
        source_file=f"{doc_id}.pdf",
        page_number=page_number,
        heading_text=heading,
        body_text=body,
        table_text=table,
        page_search_text=search,
        section_path=section_path,
        quality_floor=1.0,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_cand(
    page_number: int,
    final_score: float | None = None,
    bm25_normalized: float = 0.5,
    section_path: str = "chapter 1",
    doc_id: str = "doc",
) -> Candidate:
    return Candidate(
        page_id=f"{doc_id}::p{page_number}",
        doc_id=doc_id,
        source_file=f"{doc_id}.pdf",
        page_number=page_number,
        section_path=section_path,
        bm25_raw=float(page_number),
        bm25_normalized=bm25_normalized,
        final_score=final_score,
    )


def _body(n_tokens: int) -> str:
    return "W" * (n_tokens * _CHARS_PER_TOKEN)


assembler = EvidenceAssembler()


# ── _count_tokens ─────────────────────────────────────────────────────────────

def test_count_tokens_body_plus_table() -> None:
    page = _make_page(1, body="A" * 400, table="B" * 400)
    # combined 801 chars → ceil(801/4) = 201
    assert _count_tokens(page) == math.ceil(801 / _CHARS_PER_TOKEN)


def test_count_tokens_ignores_heading() -> None:
    page_with_heading = _make_page(1, body="A" * 100, heading="HEADING " * 50)
    page_no_heading   = _make_page(1, body="A" * 100, heading="")
    assert _count_tokens(page_with_heading) == _count_tokens(page_no_heading)


def test_count_tokens_minimum_one() -> None:
    page = _make_page(1, body="", table="", heading="only heading")
    assert _count_tokens(page) >= 1


# ── _truncate_page ────────────────────────────────────────────────────────────

def test_truncate_sets_truncated_flag() -> None:
    page = _make_page(1, body=_body(100))
    result = _truncate_page(page, 50)
    assert result.truncated is True


def test_truncate_original_unchanged() -> None:
    page = _make_page(1, body=_body(100))
    _truncate_page(page, 50)
    assert page.truncated is False  # original not mutated


def test_truncate_token_count_equals_remaining() -> None:
    page = _make_page(1, body=_body(100))
    remaining = 30
    result = _truncate_page(page, remaining)
    assert _count_tokens(result) == remaining


def test_truncate_clears_table_text() -> None:
    page = _make_page(1, body=_body(80), table=_body(40))
    result = _truncate_page(page, 50)
    assert result.table_text == ""


def test_truncate_preserves_heading() -> None:
    page = _make_page(1, body=_body(100), heading="Important Heading")
    result = _truncate_page(page, 10)
    assert result.heading_text == "Important Heading"


def test_truncate_search_text_consistent() -> None:
    page = _make_page(1, body=_body(100), table=_body(20))
    result = _truncate_page(page, 40)
    expected_search = f"{result.heading_text} {result.body_text} {result.table_text}".strip()
    assert result.page_search_text == expected_search


# ── assemble — basic ──────────────────────────────────────────────────────────

def test_assemble_returns_evidence_object() -> None:
    page = _make_page(1, body=_body(100))
    cand = _make_cand(1, final_score=0.9)
    evidence = assembler.assemble([cand], {cand.page_id: page}, "page_lookup")
    assert evidence.query_type == "page_lookup"
    assert len(evidence.pages) == 1


def test_assemble_total_tokens_within_budget() -> None:
    pages = {f"doc::p{i}": _make_page(i, body=_body(900)) for i in range(1, 6)}
    cands = [_make_cand(i, final_score=1.0 - i * 0.1) for i in range(1, 6)]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    assert evidence.total_tokens <= MAX_EVIDENCE_TOKENS


def test_assemble_token_budget_hit_when_truncated() -> None:
    pages = {f"doc::p{i}": _make_page(i, body=_body(900)) for i in range(1, 6)}
    cands = [_make_cand(i, final_score=1.0 - i * 0.1) for i in range(1, 6)]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    assert evidence.token_budget_hit is True


def test_assemble_highest_score_included_in_full() -> None:
    """Highest-scoring page processed first, always fits in full if < whole budget."""
    pages = {f"doc::p{i}": _make_page(i, body=_body(200)) for i in range(1, 6)}
    cands = [_make_cand(i, final_score=1.0 - i * 0.1) for i in range(1, 6)]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    top_page = next(p for p in evidence.pages if p.page_number == 1)
    assert top_page.truncated is False


# ── assemble — deduplication ──────────────────────────────────────────────────

def test_dedup_keeps_highest_scored_candidate() -> None:
    page = _make_page(5, body=_body(50))
    cand_low  = _make_cand(5, final_score=0.3)
    cand_high = _make_cand(5, final_score=0.9)
    evidence = assembler.assemble([cand_low, cand_high], {"doc::p5": page}, "page_lookup")
    assert len(evidence.pages) == 1


def test_dedup_removes_duplicate_page_ids() -> None:
    pages = {f"doc::p{i}": _make_page(i, body=_body(10)) for i in range(1, 4)}
    cands = [
        _make_cand(1, final_score=0.9),
        _make_cand(1, final_score=0.7),  # dup
        _make_cand(2, final_score=0.6),
        _make_cand(3, final_score=0.5),
    ]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    page_numbers = [p.page_number for p in evidence.pages]
    assert len(page_numbers) == len(set(page_numbers))


# ── assemble — section grouping ───────────────────────────────────────────────

def test_section_grouping_adjacent_pages() -> None:
    pages = {
        "doc::p1": _make_page(1, body=_body(10), section_path="chapter 1"),
        "doc::p5": _make_page(5, body=_body(10), section_path="chapter 2"),
        "doc::p3": _make_page(3, body=_body(10), section_path="chapter 1"),
    }
    cands = [
        _make_cand(1, final_score=0.9, section_path="chapter 1"),
        _make_cand(5, final_score=0.8, section_path="chapter 2"),
        _make_cand(3, final_score=0.7, section_path="chapter 1"),
    ]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    page_nums = [p.page_number for p in evidence.pages]
    # chapter 1 pages (1, 3) should be adjacent, sorted by page_number
    idx_1 = page_nums.index(1)
    idx_3 = page_nums.index(3)
    assert abs(idx_1 - idx_3) == 1


def test_within_section_sorted_by_page_number() -> None:
    pages = {f"doc::p{i}": _make_page(i, body=_body(5), section_path="ch1") for i in [3, 1, 2]}
    cands = [
        _make_cand(3, final_score=0.9, section_path="ch1"),
        _make_cand(1, final_score=0.7, section_path="ch1"),
        _make_cand(2, final_score=0.5, section_path="ch1"),
    ]
    evidence = assembler.assemble(cands, pages, "page_lookup")
    page_nums = [p.page_number for p in evidence.pages]
    assert page_nums == [1, 2, 3]


# ── assemble — dropped pages ──────────────────────────────────────────────────

def test_pages_dropped_counted_when_missing_record() -> None:
    cand = _make_cand(99, final_score=0.9)
    cand2 = _make_cand(1, final_score=0.5)
    page1 = _make_page(1, body=_body(10))
    evidence = assembler.assemble([cand, cand2], {"doc::p1": page1}, "page_lookup")
    assert evidence.pages_dropped == 1


def test_pages_dropped_counted_when_budget_exhausted() -> None:
    budget_assembler = EvidenceAssembler(token_budget=100)
    pages = {f"doc::p{i}": _make_page(i, body=_body(60)) for i in range(1, 4)}
    cands = [_make_cand(i, final_score=1.0 - i * 0.1) for i in range(1, 4)]
    evidence = budget_assembler.assemble(cands, pages, "page_lookup")
    assert evidence.pages_dropped >= 1


# ── assemble — score fallback ─────────────────────────────────────────────────

def test_uses_bm25_normalized_when_no_final_score() -> None:
    page_high = _make_page(1, body=_body(10))
    page_low  = _make_page(2, body=_body(10))
    cand_high = _make_cand(1, final_score=None, bm25_normalized=0.9)
    cand_low  = _make_cand(2, final_score=None, bm25_normalized=0.2)
    pages = {"doc::p1": page_high, "doc::p2": page_low}
    budget_assembler = EvidenceAssembler(token_budget=15)  # fits only one
    evidence = budget_assembler.assemble([cand_low, cand_high], pages, "page_lookup")
    # page 1 (higher bm25) should win
    assert any(p.page_number == 1 for p in evidence.pages)


# ── empty evidence guard ──────────────────────────────────────────────────────

def test_empty_evidence_raises_empty_evidence_error() -> None:
    with pytest.raises(EmptyEvidenceError):
        assembler.assemble([], {}, "page_lookup")


def test_missing_all_records_raises_empty_evidence_error() -> None:
    cand = _make_cand(1, final_score=0.9)
    with pytest.raises(EmptyEvidenceError):
        assembler.assemble([cand], {}, "page_lookup")
