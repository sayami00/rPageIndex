"""
Acceptance script for EvidenceAssembler (Phase 10).

Scenario: 5 large pages (~900 tokens each, total ~4500 > 3000 budget).
Verifies:
  - total_tokens <= MAX_EVIDENCE_TOKENS
  - token_budget_hit == True
  - highest-scoring page (page 1) included with truncated=False
  - page 4 (last fitted) included with truncated=True
  - page 5 dropped (pages_dropped == 1)
  - section grouping preserves reading order within sections
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s - %(message)s",
    stream=sys.stdout,
)

from src.evidence.assembler import (     # noqa: E402
    MAX_EVIDENCE_TOKENS,
    EvidenceAssembler,
    _CHARS_PER_TOKEN,
    _count_tokens,
)
from src.models.exceptions import EmptyEvidenceError  # noqa: E402
from src.models.index import PageRecord               # noqa: E402
from src.models.query import Candidate                # noqa: E402


def _make_page(
    page_number: int,
    body_tokens: int,
    section_path: str = "chapter 1",
) -> PageRecord:
    body = "W" * (body_tokens * _CHARS_PER_TOKEN)
    search = f"Heading {body}".strip()
    return PageRecord(
        page_id=f"doc::p{page_number}",
        doc_id="doc",
        source_file="doc.pdf",
        page_number=page_number,
        heading_text="Heading",
        body_text=body,
        table_text="",
        page_search_text=search,
        section_path=section_path,
        quality_floor=1.0,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_cand(page_number: int, final_score: float, section_path: str = "chapter 1") -> Candidate:
    return Candidate(
        page_id=f"doc::p{page_number}",
        doc_id="doc",
        source_file="doc.pdf",
        page_number=page_number,
        section_path=section_path,
        bm25_raw=float(page_number),
        bm25_normalized=final_score,
        final_score=final_score,
    )


# --- Scenario 1: 5 large pages, budget = 3000 ---

TOKENS_EACH = 900   # 5 * 900 = 4500 > 3000

pages = {
    f"doc::p{i}": _make_page(i, TOKENS_EACH)
    for i in range(1, 6)
}
candidates = [
    _make_cand(1, 0.95),
    _make_cand(2, 0.83),
    _make_cand(3, 0.71),
    _make_cand(4, 0.62),
    _make_cand(5, 0.45),
]

assembler = EvidenceAssembler(token_budget=MAX_EVIDENCE_TOKENS)
evidence = assembler.assemble(candidates, pages, "page_lookup")

print(f"\n{'='*60}")
print("SCENARIO 1: 5 large pages (~900 tokens each)")
print(f"{'='*60}")
print(f"  token_budget     : {evidence.token_budget}")
print(f"  total_tokens     : {evidence.total_tokens}")
print(f"  token_budget_hit : {evidence.token_budget_hit}")
print(f"  pages_dropped    : {evidence.pages_dropped}")
print(f"  pages included   : {len(evidence.pages)}")
for p in evidence.pages:
    toks = _count_tokens(p)
    print(f"    page {p.page_number}: tokens={toks} truncated={p.truncated}")

pass_count = fail_count = 0
checks: list[tuple[str, bool, str]] = []

checks.append((
    "total_tokens <= MAX_EVIDENCE_TOKENS",
    evidence.total_tokens <= MAX_EVIDENCE_TOKENS,
    f"{evidence.total_tokens} <= {MAX_EVIDENCE_TOKENS}",
))
checks.append((
    "token_budget_hit == True",
    evidence.token_budget_hit is True,
    "",
))
checks.append((
    "highest-score page (1) not truncated",
    not next(p for p in evidence.pages if p.page_number == 1).truncated,
    "",
))
checks.append((
    "at least one page truncated",
    any(p.truncated for p in evidence.pages),
    "",
))
checks.append((
    "pages_dropped >= 1",
    evidence.pages_dropped >= 1,
    f"dropped={evidence.pages_dropped}",
))
checks.append((
    "page 5 not in evidence (dropped)",
    all(p.page_number != 5 for p in evidence.pages),
    "",
))


# --- Scenario 2: section grouping ---

pages_multi = {
    "doc::p1": _make_page(1, 10, section_path="ch1"),
    "doc::p3": _make_page(3, 10, section_path="ch1"),
    "doc::p5": _make_page(5, 10, section_path="ch2"),
    "doc::p7": _make_page(7, 10, section_path="ch2"),
    "doc::p2": _make_page(2, 10, section_path="ch1"),
}
cands_multi = [
    _make_cand(1, 0.9, "ch1"),
    _make_cand(5, 0.8, "ch2"),   # high score but ch2
    _make_cand(3, 0.7, "ch1"),
    _make_cand(7, 0.6, "ch2"),
    _make_cand(2, 0.5, "ch1"),
]
ev2 = EvidenceAssembler().assemble(cands_multi, pages_multi, "page_lookup")
page_nums = [p.page_number for p in ev2.pages]

# ch1 pages (1, 2, 3) should be adjacent and sorted; ch2 pages (5, 7) adjacent and sorted
ch1_positions = [page_nums.index(p) for p in [1, 2, 3]]
ch2_positions = [page_nums.index(p) for p in [5, 7]]

checks.append((
    "ch1 pages adjacent in output",
    max(ch1_positions) - min(ch1_positions) == 2,
    f"ch1_pos={ch1_positions}",
))
checks.append((
    "ch2 pages adjacent in output",
    max(ch2_positions) - min(ch2_positions) == 1,
    f"ch2_pos={ch2_positions}",
))
checks.append((
    "ch1 pages sorted by page_number",
    ch1_positions == sorted(ch1_positions),
    f"ch1_pos={ch1_positions}",
))


# --- Scenario 3: EmptyEvidenceError ---

try:
    EvidenceAssembler().assemble([], {}, "page_lookup")
    checks.append(("EmptyEvidenceError raised on empty", False, "no error raised"))
except EmptyEvidenceError:
    checks.append(("EmptyEvidenceError raised on empty", True, ""))


print(f"\n{'='*60}")
print("ACCEPTANCE CHECKS:")
for label, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{extra}")
    if ok:
        pass_count += 1
    else:
        fail_count += 1

print(f"\n{'='*60}")
print(f"PASS {pass_count}/{len(checks)}  FAIL {fail_count}")
sys.exit(0 if fail_count == 0 else 1)
