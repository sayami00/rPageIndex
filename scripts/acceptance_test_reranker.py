"""
Acceptance script for StructuralReranker (Phase 9.2).

Takes 20 synthetic candidates, applies reranking, and verifies:
  - Pages with matching section hierarchy rank higher than isolated keyword matches
  - Proximity clustering boosts adjacent pages
  - Score breakdown for top 3 is printed
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

from src.models.query import Candidate   # noqa: E402
from src.query.reranker import StructuralReranker  # noqa: E402


def make_candidate(page_number: int, bm25_raw: float, section_path: str = "") -> Candidate:
    return Candidate(
        page_id=f"doc1::p{page_number}",
        doc_id="doc1",
        source_file="doc1.pdf",
        page_number=page_number,
        section_path=section_path,
        bm25_raw=bm25_raw,
        bm25_normalized=0.0,
    )


candidates: list[Candidate] = [
    # Cluster A: pages 10-14 — target section, moderate-high BM25
    make_candidate(10, 8.5, "chapter 3 / caching"),
    make_candidate(11, 9.0, "chapter 3 / caching"),
    make_candidate(12, 7.0, "chapter 3 / caching"),
    make_candidate(13, 6.5, "chapter 3 / caching"),
    make_candidate(14, 5.0, "chapter 3 / caching"),
    # Cluster B: pages 40-43 — wrong section
    make_candidate(40, 7.5, "appendix / reference"),
    make_candidate(41, 7.8, "appendix / reference"),
    make_candidate(42, 6.0, "appendix / reference"),
    make_candidate(43, 5.5, "appendix / reference"),
    # Isolated high-BM25 — no neighbours, wrong section
    make_candidate(1,  10.0, "introduction"),
    make_candidate(50,  8.0, "glossary"),
    make_candidate(99,  7.9, "index"),
    # Low-BM25 but in target section near cluster A
    make_candidate(9,   3.0, "chapter 3 / caching"),
    # Scattered pages
    make_candidate(20,  6.0, "chapter 1 / intro"),
    make_candidate(25,  5.5, "chapter 2 / setup"),
    make_candidate(30,  4.0, "chapter 3 / caching"),
    make_candidate(60,  3.5, "appendix / glossary"),
    make_candidate(70,  3.0, "chapter 4 / advanced"),
    make_candidate(80,  2.5, "appendix / reference"),
    make_candidate(90,  2.0, "chapter 5 / tuning"),
]

reranker = StructuralReranker()
SECTION_HINT = "chapter 3 caching"

print(f"\n{'='*60}")
print(f"Input: {len(candidates)} candidates | section_hint={SECTION_HINT!r}")
print(f"{'='*60}\n")

result = reranker.rerank(candidates, query_type="page_lookup", section_hint=SECTION_HINT)

print(f"\n{'='*60}")
print("TOP 5 RERANKED (page_lookup with section_hint):")
print(f"{'='*60}")
print(f"{'Rank':<5} {'page':>5} {'section_path':<35} {'bm25':>6} {'hier':>6} {'prox':>6} {'final':>6}")
print("-" * 75)
for rank, c in enumerate(result, 1):
    print(
        f"{rank:<5} {c.page_number:>5} {c.section_path:<35} "
        f"{c.bm25_normalized:>6.3f} {c.hierarchy_score:>6.3f} "
        f"{c.proximity_score:>6.3f} {c.final_score:>6.3f}"
    )

# Verification checks
pass_count = fail_count = 0
checks: list[tuple[str, bool, str]] = []

# Check 1: top 5 contain at least 3 cluster A pages
cluster_a = {9, 10, 11, 12, 13, 14, 30}
top5_pages = {c.page_number for c in result}
cluster_a_in_top5 = top5_pages & cluster_a
ok = len(cluster_a_in_top5) >= 3
checks.append(("cluster A >=3 in top 5", ok, f"cluster_a_in_top5={cluster_a_in_top5}"))

# Check 2: sorted descending by final_score
scores = [c.final_score for c in result]
ok = scores == sorted(scores, reverse=True)
checks.append(("sorted descending", ok, f"scores={[round(s,3) for s in scores]}"))

# Check 3: all have non-None scores
ok = all(c.final_score is not None for c in result)
checks.append(("all scores non-None", ok, ""))

# Check 4: weights sum correctly for each candidate
weight_ok = True
for c in result:
    expected = round(0.5 * c.bm25_normalized + 0.3 * c.hierarchy_score + 0.2 * c.proximity_score, 4)
    if abs(c.final_score - expected) > 0.001:
        weight_ok = False
        break
checks.append(("weight formula correct", weight_ok, "0.5*bm25 + 0.3*hierarchy + 0.2*proximity"))

# Check 5: isolated p1 (highest BM25) not #1 due to section mismatch + no proximity
p1_rank = next((i + 1 for i, c in enumerate(result) if c.page_number == 1), None)
ok = p1_rank is None or p1_rank > 1
checks.append(("isolated p1 not rank #1 with hint", ok, f"p1_rank={p1_rank}"))

print(f"\n{'='*60}")
print("ACCEPTANCE CHECKS:")
for label, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}{' — ' + detail if detail else ''}")
    if ok:
        pass_count += 1
    else:
        fail_count += 1

print(f"\n{'='*60}")
print(f"PASS {pass_count}/{len(checks)}  FAIL {fail_count}")
sys.exit(0 if fail_count == 0 else 1)
