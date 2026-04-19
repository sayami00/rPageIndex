from __future__ import annotations

import pytest

from src.answer.verifier import CitationVerifier
from src.models.answer import RawAnswer, VerifiedAnswer
from src.models.index import PageRecord
from src.models.query import Evidence


def _make_page(page_number: int, source_file: str = "doc.pdf") -> PageRecord:
    return PageRecord(
        page_id=f"{source_file}::p{page_number}",
        doc_id="doc",
        source_file=source_file,
        page_number=page_number,
        heading_text="Heading",
        body_text="Some body text.",
        table_text="",
        page_search_text="Heading Some body text.",
        section_path="chapter 1",
        quality_floor=1.0,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_evidence(pages: list[PageRecord]) -> Evidence:
    return Evidence(
        pages=pages,
        total_tokens=100,
        token_budget=3000,
        token_budget_hit=False,
        pages_dropped=0,
        query_type="page_lookup",
    )


def _make_raw(
    body: str = "The answer.",
    citations: list[str] | None = None,
    latency_ms: int = 50,
) -> RawAnswer:
    if citations is None:
        citations = ["[file: doc.pdf, page: 3]"]
    return RawAnswer(
        answer_text=body,
        answer_body=body,
        raw_citations=citations,
        model_used="qwen:7b",
        input_tokens=100,
        output_tokens=20,
        latency_ms=latency_ms,
        token_budget_hit=False,
    )


# page_store covers doc.pdf p1-10, infra.pdf p1-5
_PAGE_STORE: set[tuple[str, int]] = (
    {("doc.pdf", i) for i in range(1, 11)} |
    {("infra.pdf", i) for i in range(1, 6)}
)
# evidence covers doc.pdf p1-5 only
_EVIDENCE_PAGES = [_make_page(i) for i in range(1, 6)]
_EV = _make_evidence(_EVIDENCE_PAGES)
_VERIFIER = CitationVerifier(_PAGE_STORE)


# ── status checks ─────────────────────────────────────────────────────────────

def test_valid_citation() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.citations[0].status == "VALID"
    assert result.valid_citation_count == 1
    assert result.invalid_citation_count == 0


def test_hallucinated_not_in_corpus() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 999]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.citations[0].status == "HALLUCINATED"
    assert result.valid_citation_count == 0
    assert result.invalid_citation_count == 1


def test_out_of_scope_in_corpus_not_in_evidence() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 8]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.citations[0].status == "OUT_OF_SCOPE"
    assert result.valid_citation_count == 0
    assert result.invalid_citation_count == 1


def test_multi_file_valid_in_evidence() -> None:
    ev = _make_evidence(_EVIDENCE_PAGES + [_make_page(2, "infra.pdf")])
    raw = _make_raw(citations=["[file: infra.pdf, page: 2]"])
    result = CitationVerifier(_PAGE_STORE).verify(raw, ev, "query", "page_lookup")
    assert result.citations[0].status == "VALID"


def test_mixed_citations() -> None:
    raw = _make_raw(citations=[
        "[file: doc.pdf, page: 3]",    # VALID
        "[file: doc.pdf, page: 999]",  # HALLUCINATED
        "[file: doc.pdf, page: 8]",    # OUT_OF_SCOPE
    ])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    statuses = {c.raw_citation: c.status for c in result.citations}
    assert statuses["[file: doc.pdf, page: 3]"] == "VALID"
    assert statuses["[file: doc.pdf, page: 999]"] == "HALLUCINATED"
    assert statuses["[file: doc.pdf, page: 8]"] == "OUT_OF_SCOPE"
    assert result.valid_citation_count == 1
    assert result.invalid_citation_count == 2


# ── disclaimer ────────────────────────────────────────────────────────────────

def test_disclaimer_appended_when_all_invalid() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 999]", "[file: doc.pdf, page: 998]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.disclaimer_appended is True
    assert "no source pages could be verified" in result.answer


def test_no_disclaimer_when_some_valid() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]", "[file: doc.pdf, page: 999]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.disclaimer_appended is False


def test_no_disclaimer_when_no_citations() -> None:
    raw = _make_raw(citations=[])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.disclaimer_appended is False


# ── answer rebuild ─────────────────────────────────────────────────────────────

def test_rebuilt_answer_contains_only_valid_citations() -> None:
    raw = _make_raw(citations=[
        "[file: doc.pdf, page: 3]",
        "[file: doc.pdf, page: 999]",
    ])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert "page: 3" in result.answer
    assert "page: 999" not in result.answer


def test_rebuilt_answer_includes_citations_block() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert "CITATIONS:" in result.answer


def test_rebuilt_answer_body_preserved() -> None:
    raw = _make_raw(body="Cache size is 4GB.", citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert "Cache size is 4GB." in result.answer


# ── status detection ──────────────────────────────────────────────────────────

def test_status_not_found_phrase() -> None:
    raw = _make_raw(body="This is not in the provided documents.", citations=[])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.status == "not_found"


def test_status_answered() -> None:
    raw = _make_raw(body="The cache is 4GB.", citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.status == "answered"


# ── counts and fields ─────────────────────────────────────────────────────────

def test_all_citations_valid_true() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.all_citations_valid is True


def test_all_citations_valid_false_when_invalid() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]", "[file: doc.pdf, page: 999]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.all_citations_valid is False


def test_all_citations_valid_false_when_no_citations() -> None:
    raw = _make_raw(citations=[])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.all_citations_valid is False


def test_query_original_and_type_preserved() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "What is the cache?", "table_query")
    assert result.query_original == "What is the cache?"
    assert result.query_type == "table_query"


def test_latency_ms_total_adds_verification_time() -> None:
    raw = _make_raw(latency_ms=100, citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.latency_ms_total >= 100


def test_returns_verified_answer_instance() -> None:
    raw = _make_raw(citations=["[file: doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert isinstance(result, VerifiedAnswer)


def test_citation_source_file_is_basename() -> None:
    raw = _make_raw(citations=["[file: /some/long/path/doc.pdf, page: 3]"])
    result = _VERIFIER.verify(raw, _EV, "query", "page_lookup")
    assert result.citations[0].source_file == "doc.pdf"
    assert "/" not in result.citations[0].source_file
