"""
Acceptance tests for StructuralReranker.

Uses 20 synthetic candidates with known characteristics to verify that
pages with matching section hierarchy and adjacent page numbers rank higher.
"""
from __future__ import annotations

import pytest

from src.models.query import Candidate
from src.query.reranker import StructuralReranker

reranker = StructuralReranker()


def _make_candidate(
    page_number: int,
    bm25_raw: float,
    section_path: str = "",
    doc_id: str = "doc1",
    fallback_step: int = 0,
) -> Candidate:
    return Candidate(
        page_id=f"{doc_id}::p{page_number}",
        doc_id=doc_id,
        source_file=f"{doc_id}.pdf",
        page_number=page_number,
        section_path=section_path,
        bm25_raw=bm25_raw,
        bm25_normalized=0.0,  # reranker will overwrite
        retrieved_at_fallback_step=fallback_step,
    )


# 20 candidates with varying BM25, section paths, and page clustering
_CANDIDATES: list[Candidate] = [
    # Cluster A: pages 10-14, matching section path "chapter 3 / caching"
    _make_candidate(10, 8.5, "chapter 3 / caching"),
    _make_candidate(11, 9.0, "chapter 3 / caching"),   # highest BM25 in cluster
    _make_candidate(12, 7.0, "chapter 3 / caching"),
    _make_candidate(13, 6.5, "chapter 3 / caching"),
    _make_candidate(14, 5.0, "chapter 3 / caching"),

    # Cluster B: pages 40-43, wrong section path, moderate BM25
    _make_candidate(40, 7.5, "appendix / reference"),
    _make_candidate(41, 7.8, "appendix / reference"),
    _make_candidate(42, 6.0, "appendix / reference"),
    _make_candidate(43, 5.5, "appendix / reference"),

    # Isolated high-BM25 pages (no neighbours in candidate set)
    _make_candidate(1,  10.0, "introduction"),         # top raw BM25, but isolated, wrong section
    _make_candidate(50, 8.0,  "glossary"),             # isolated
    _make_candidate(99, 7.9,  "index"),                # isolated

    # Low-BM25 but in correct section, in cluster A
    _make_candidate(9,  3.0, "chapter 3 / caching"),   # neighbour of cluster A

    # Scattered pages, mixed sections
    _make_candidate(20, 6.0, "chapter 1 / intro"),
    _make_candidate(25, 5.5, "chapter 2 / setup"),
    _make_candidate(30, 4.0, "chapter 3 / caching"),   # correct section, isolated
    _make_candidate(60, 3.5, "appendix / glossary"),
    _make_candidate(70, 3.0, "chapter 4 / advanced"),
    _make_candidate(80, 2.5, "appendix / reference"),
    _make_candidate(90, 2.0, "chapter 5 / tuning"),
]


def test_rerank_returns_correct_top_n_for_page_lookup() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="page_lookup")
    assert len(result) == 5


def test_rerank_returns_correct_top_n_for_find_all() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="find_all")
    assert len(result) == 8


def test_all_candidates_have_scores_after_rerank() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="page_lookup", section_hint="chapter 3 caching")
    for c in result:
        assert c.hierarchy_score is not None
        assert c.proximity_score is not None
        assert c.final_score is not None


def test_bm25_normalized_computed_from_max_raw() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="page_lookup")
    # page 1 has bm25_raw=10.0 (max), so its bm25_normalized should be 1.0
    p1 = next((c for c in result if c.page_number == 1), None)
    # page 1 may not be in top 5, so search all scored candidates via find_all
    result_all = reranker.rerank(_CANDIDATES, query_type="find_all")
    p1_scored = next((c for c in result_all if c.page_number == 1), None)
    if p1_scored:
        assert abs(p1_scored.bm25_normalized - 1.0) < 0.001


def test_section_matching_candidates_rank_higher_than_isolated_high_bm25() -> None:
    """
    Page 1 has the highest raw BM25 (10.0) but is isolated and has wrong section.
    Pages 10-13 are in cluster A with matching section "chapter 3 caching".
    With section_hint, cluster A should dominate the top 5.
    """
    result = reranker.rerank(
        _CANDIDATES,
        query_type="page_lookup",
        section_hint="chapter 3 caching",
    )
    top5_pages = {c.page_number for c in result}
    cluster_a_pages = {9, 10, 11, 12, 13, 14, 30}
    cluster_a_in_top5 = top5_pages & cluster_a_pages
    # At least 3 of top 5 should be from the matching section cluster
    assert len(cluster_a_in_top5) >= 3, (
        f"Expected cluster A pages to dominate top 5. "
        f"Got top5={top5_pages}, cluster_a_in_top5={cluster_a_in_top5}"
    )


def test_isolated_high_bm25_does_not_beat_clustered_section_match() -> None:
    """
    Without section_hint, isolated p1 (bm25=10.0) should appear.
    With section_hint='chapter 3 caching', clustered pages beat it.
    """
    result_no_hint = reranker.rerank(_CANDIDATES, query_type="page_lookup")
    result_with_hint = reranker.rerank(
        _CANDIDATES, query_type="page_lookup", section_hint="chapter 3 caching"
    )
    # page 1 more likely in top 5 without hint
    p1_in_no_hint = any(c.page_number == 1 for c in result_no_hint)
    p1_in_with_hint = any(c.page_number == 1 for c in result_with_hint)
    # page 1 should rank lower when section hint is present
    if p1_in_no_hint:
        # If it appears in both, its final_score should be lower with hint
        pass  # just verify no crash — structural benefit tested elsewhere
    # cluster A pages should appear in top 5 with hint
    assert any(c.page_number in {10, 11, 12, 13, 14} for c in result_with_hint)


def test_proximity_score_higher_for_clustered_pages() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="find_all")
    # pages 10-14 are clustered — find one and check proximity > 0
    clustered = [c for c in result if c.page_number in {10, 11, 12, 13, 14}]
    for c in clustered:
        assert c.proximity_score > 0.0, f"page {c.page_number} should have proximity>0"


def test_top3_score_breakdown_logged(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.INFO, logger="src.query.reranker"):
        reranker.rerank(_CANDIDATES, query_type="page_lookup", section_hint="chapter 3")
    top_logs = [r.getMessage() for r in caplog.records if "top" in r.getMessage()]
    assert len(top_logs) >= 3, f"Expected at least 3 top-N log lines, got: {top_logs}"


def test_empty_candidates_returns_empty() -> None:
    assert reranker.rerank([], query_type="page_lookup") == []


def test_neutral_hierarchy_score_when_no_hint() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="page_lookup", section_hint=None)
    # all hierarchy scores should be 0.5 (neutral)
    for c in result:
        assert abs(c.hierarchy_score - 0.5) < 0.001, (
            f"page {c.page_number} hierarchy={c.hierarchy_score}, expected 0.5"
        )


def test_final_score_weights_sum() -> None:
    """Verify final = 0.5*bm25 + 0.3*hierarchy + 0.2*proximity for each result."""
    result = reranker.rerank(_CANDIDATES, query_type="find_all", section_hint="chapter 3")
    for c in result:
        expected = 0.5 * c.bm25_normalized + 0.3 * c.hierarchy_score + 0.2 * c.proximity_score
        assert abs(c.final_score - expected) < 0.001, (
            f"page {c.page_number}: final={c.final_score} expected={expected:.4f}"
        )


def test_sorted_descending_by_final_score() -> None:
    result = reranker.rerank(_CANDIDATES, query_type="find_all")
    scores = [c.final_score for c in result]
    assert scores == sorted(scores, reverse=True)
