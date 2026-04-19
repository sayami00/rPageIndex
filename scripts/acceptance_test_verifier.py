"""
Acceptance script for CitationVerifier (Phase 11.5).

page_store: doc.pdf pages 1-10, infra.pdf pages 1-5
evidence:   doc.pdf pages 1-5 only

10 scenarios covering VALID, HALLUCINATED, OUT_OF_SCOPE, disclaimer, multi-file.
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s - %(message)s",
    stream=sys.stdout,
)

from src.answer.verifier import CitationVerifier          # noqa: E402
from src.models.answer import RawAnswer                   # noqa: E402
from src.models.index import PageRecord                   # noqa: E402
from src.models.query import Evidence                     # noqa: E402


def _make_page(page_number: int, source_file: str = "doc.pdf") -> PageRecord:
    return PageRecord(
        page_id=f"{source_file}::p{page_number}",
        doc_id="doc",
        source_file=source_file,
        page_number=page_number,
        heading_text="Heading",
        body_text="Content.",
        table_text="",
        page_search_text="Heading Content.",
        section_path="chapter 1",
        quality_floor=1.0,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_raw(body: str, citations: list[str], latency_ms: int = 50) -> RawAnswer:
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


# corpus: doc.pdf p1-10, infra.pdf p1-5
PAGE_STORE: set[tuple[str, int]] = (
    {("doc.pdf", i) for i in range(1, 11)} |
    {("infra.pdf", i) for i in range(1, 6)}
)

# evidence: doc.pdf p1-5, infra.pdf p2
EV_PAGES = [_make_page(i) for i in range(1, 6)] + [_make_page(2, "infra.pdf")]
EVIDENCE = Evidence(
    pages=EV_PAGES,
    total_tokens=200,
    token_budget=3000,
    token_budget_hit=False,
    pages_dropped=0,
    query_type="page_lookup",
)

VERIFIER = CitationVerifier(PAGE_STORE)

# (description, raw_answer, check_fn)
SCENARIOS = [
    # 1. injected hallucination
    (
        "Injected hallucination - doc.pdf page 999",
        _make_raw("Answer text.", ["[file: doc.pdf, page: 999]"]),
        lambda r: r.citations[0].status == "HALLUCINATED" and r.disclaimer_appended,
    ),
    # 2. out-of-scope page (in corpus, not in evidence)
    (
        "Out-of-scope page - doc.pdf page 8",
        _make_raw("Answer text.", ["[file: doc.pdf, page: 8]"]),
        lambda r: r.citations[0].status == "OUT_OF_SCOPE" and r.disclaimer_appended,
    ),
    # 3. valid citation
    (
        "Valid citation - doc.pdf page 3",
        _make_raw("Cache is 4GB.", ["[file: doc.pdf, page: 3]"]),
        lambda r: r.citations[0].status == "VALID" and r.valid_citation_count == 1,
    ),
    # 4. multi-file valid (infra.pdf in evidence)
    (
        "Multi-file valid - infra.pdf page 2",
        _make_raw("Server config.", ["[file: infra.pdf, page: 2]"]),
        lambda r: r.citations[0].status == "VALID",
    ),
    # 5. all invalid -> disclaimer
    (
        "All invalid -> disclaimer - pages 999, 998",
        _make_raw("Some answer.", ["[file: doc.pdf, page: 999]", "[file: doc.pdf, page: 998]"]),
        lambda r: r.disclaimer_appended and r.valid_citation_count == 0 and "no source pages" in r.answer,
    ),
    # 6. mixed - valid + hallucinated
    (
        "Mixed: valid + hallucinated",
        _make_raw("Combined answer.", ["[file: doc.pdf, page: 3]", "[file: doc.pdf, page: 999]"]),
        lambda r: r.valid_citation_count == 1 and r.invalid_citation_count == 1 and not r.disclaimer_appended,
    ),
    # 7. no citations -> no disclaimer, no CITATIONS block in rebuilt
    (
        "No citations - empty list",
        _make_raw("Plain answer.", []),
        lambda r: not r.disclaimer_appended and r.valid_citation_count == 0 and r.all_citations_valid is False,
    ),
    # 8. not_found status detection
    (
        "Status: not_found phrase in body",
        _make_raw("This is not in the provided documents.", ["[file: doc.pdf, page: 3]"]),
        lambda r: r.status == "not_found",
    ),
    # 9. answered status
    (
        "Status: answered - normal answer",
        _make_raw("Cache size is 4GB on web01.", ["[file: doc.pdf, page: 3]"]),
        lambda r: r.status == "answered",
    ),
    # 10. latency_ms_total >= raw latency
    (
        "Latency: total >= raw_answer latency",
        _make_raw("Answer.", ["[file: doc.pdf, page: 3]"], latency_ms=75),
        lambda r: r.latency_ms_total >= 75,
    ),
]

pass_count = fail_count = 0
print(f"\n{'='*65}")
print("PHASE 11.5 CITATION VERIFIER ACCEPTANCE TEST")
print(f"{'='*65}\n")

for idx, (desc, raw, check) in enumerate(SCENARIOS, 1):
    result = VERIFIER.verify(raw, EVIDENCE, f"query {idx}", "page_lookup")
    ok = check(result)
    status = "PASS" if ok else "FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1
    print(f"[{status}] {idx:2}. {desc}")
    if not ok:
        print(f"         valid={result.valid_citation_count} invalid={result.invalid_citation_count} "
              f"disclaimer={result.disclaimer_appended} status={result.status!r}")
        for c in result.citations:
            print(f"           {c.source_file} p{c.page_number} -> {c.status}")
    else:
        print(f"         valid={result.valid_citation_count} invalid={result.invalid_citation_count} "
              f"disclaimer={result.disclaimer_appended} latency={result.latency_ms_total}ms")

print(f"\n{'='*65}")
print(f"PASS {pass_count}/10  FAIL {fail_count}")
sys.exit(0 if fail_count == 0 else 1)
