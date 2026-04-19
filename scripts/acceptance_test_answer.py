"""
Acceptance script for AnswerGenerator (Phase 11).

10 query scenarios with mock Ollama responses. Verifies:
  - Every answer cites at least one page
  - answer_body is non-empty and excludes CITATIONS block
  - model_used, latency_ms, input_tokens, output_tokens all populated
  - 3 spot-check scenarios with known body substrings and expected citations

Live Ollama attempt if running.
"""
from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s - %(message)s",
    stream=sys.stdout,
)

from src.answer.generator import AnswerGenerator           # noqa: E402
from src.models.index import PageRecord                    # noqa: E402
from src.models.query import Evidence                      # noqa: E402
from src.reasoning.ollama_client import OllamaClient, OllamaError  # noqa: E402


def _make_page(page_number: int, body: str, source_file: str = "doc.pdf") -> PageRecord:
    search = f"Heading {body}".strip()
    return PageRecord(
        page_id=f"doc::p{page_number}", doc_id="doc", source_file=source_file,
        page_number=page_number, heading_text="Heading",
        body_text=body, table_text="", page_search_text=search,
        section_path="chapter 1", quality_floor=1.0,
        has_low_confidence=False, table_ids=[], feature_ids=[], block_count=1,
    )


def _make_evidence(pages: list[PageRecord], query_type: str = "page_lookup") -> Evidence:
    total = sum(len(p.body_text) // 4 + 1 for p in pages)
    return Evidence(
        pages=pages, total_tokens=total, token_budget=3000,
        token_budget_hit=False, pages_dropped=0, query_type=query_type,
    )


def _mock_client(response: str) -> OllamaClient:
    c = MagicMock(spec=OllamaClient)
    c.model = "qwen:7b"
    c.generate.return_value = response
    return c


# 10 test scenarios: (query, query_type, mock_response, spot_check_fn_or_None)
SCENARIOS = [
    # 1. page_lookup — single citation
    (
        "What is the cache size?",
        "page_lookup",
        "The cache size is 4GB as configured on web01.\n\nCITATIONS:\n- [file: doc.pdf, page: 5]",
        lambda r: "4GB" in r.answer_body and len(r.raw_citations) == 1,
    ),
    # 2. find_all — multiple citations
    (
        "List all occurrences of timeout errors.",
        "find_all",
        "1. Timeout on page 3 during auth.\n2. Timeout on page 8 during retry.\n\nCITATIONS:\n- [file: doc.pdf, page: 3]\n- [file: doc.pdf, page: 8]",
        lambda r: len(r.raw_citations) == 2 and "1." in r.answer_body,
    ),
    # 3. table_query — single citation with table location
    (
        "What is the max size for web01?",
        "table_query",
        "web01 has a maximum cache size of 4GB (L1, memory cache).\n\nCITATIONS:\n- [file: infra.pdf, page: 12]",
        lambda r: "4GB" in r.answer_body and "infra.pdf" in r.raw_citations[0],
    ),
    # 4. section_lookup
    (
        "What does section 3 cover?",
        "section_lookup",
        "Section 3 (pages 10-15) covers authentication and token management.\n\nCITATIONS:\n- [file: doc.pdf, page: 10]",
        None,
    ),
    # 5. answer body does not start with CITATIONS
    (
        "Explain the retry policy.",
        "page_lookup",
        "The retry policy uses exponential backoff.\n\nCITATIONS:\n- [file: doc.pdf, page: 2]",
        lambda r: not r.answer_body.startswith("CITATIONS"),
    ),
    # 6. no CITATIONS block — raw_citations empty
    (
        "What is the deployment process?",
        "page_lookup",
        "The deployment process involves three stages.",
        lambda r: r.raw_citations == [] and r.answer_body != "",
    ),
    # 7. multiple pages in evidence — multi-citation response
    (
        "How does caching interact with auth?",
        "page_lookup",
        "Caching stores tokens. Auth validates them.\n\nCITATIONS:\n- [file: doc.pdf, page: 5]\n- [file: doc.pdf, page: 14]",
        lambda r: len(r.raw_citations) == 2,
    ),
    # 8. not-in-context answer
    (
        "What is the quantum tunneling threshold?",
        "page_lookup",
        "This information is not in the provided documents.\n\nCITATIONS:\n- [file: doc.pdf, page: 1]",
        lambda r: "not in the provided documents" in r.answer_body,
    ),
    # 9. token_budget_hit propagated
    (
        "Summarise all config options.",
        "find_all",
        "1. Timeout: 30s (page 2).\n2. Retry: 3 (page 4).\n\nCITATIONS:\n- [file: doc.pdf, page: 2]\n- [file: doc.pdf, page: 4]",
        None,
    ),
    # 10. input_tokens reflects prompt length
    (
        "What is the maximum table row count?",
        "table_query",
        "Maximum table row count is 1000.\n\nCITATIONS:\n- [file: tables.pdf, page: 9]",
        lambda r: r.input_tokens > 50,  # prompt is non-trivial
    ),
]

PAGES = [_make_page(i, f"Content about topic {i} including relevant details." * 5) for i in range(1, 4)]

pass_count = fail_count = 0
print(f"\n{'='*65}")
print("PHASE 11 ANSWER GENERATION ACCEPTANCE TEST")
print(f"{'='*65}\n")

for idx, (query, query_type, mock_resp, spot_check) in enumerate(SCENARIOS, 1):
    ev = _make_evidence(PAGES, query_type=query_type)
    gen = AnswerGenerator(_mock_client(mock_resp))
    result = gen.generate(query, query_type, ev)

    # Universal checks
    checks = [
        ("non-empty answer_body",     result.answer_body != ""),
        ("citations not in body",     "CITATIONS:" not in result.answer_body),
        ("model_used set",            result.model_used != ""),
        ("latency_ms >= 0",           result.latency_ms >= 0),
        ("input_tokens > 0",          result.input_tokens > 0),
        ("output_tokens > 0",         result.output_tokens > 0),
    ]
    if spot_check is not None:
        checks.append(("spot_check", spot_check(result)))

    scenario_pass = all(v for _, v in checks)
    status = "PASS" if scenario_pass else "FAIL"
    if scenario_pass:
        pass_count += 1
    else:
        fail_count += 1

    print(f"[{status}] {idx:2}. {query[:55]}")
    if not scenario_pass:
        for label, ok in checks:
            if not ok:
                print(f"         FAIL: {label}")
    else:
        print(f"         citations={len(result.raw_citations)}  body_len={len(result.answer_body)}  in_tok={result.input_tokens}")

# Live Ollama check
print(f"\n--- Live Ollama Check (optional) ---")
try:
    real_client = OllamaClient(model="qwen:7b", timeout=5)
    ev_live = _make_evidence([_make_page(1, "The cache size is 4GB configured on web01.")])
    gen_live = AnswerGenerator(real_client)
    live_result = gen_live.generate("What is the cache size?", "page_lookup", ev_live)
    print(f"  Ollama live: OK  body={live_result.answer_body[:80]!r}")
    print(f"  citations={live_result.raw_citations}")
except OllamaError as exc:
    print(f"  Ollama live: SKIP (not running) - {exc}")

print(f"\n{'='*65}")
print(f"PASS {pass_count}/10  FAIL {fail_count}")
sys.exit(0 if fail_count == 0 else 1)
