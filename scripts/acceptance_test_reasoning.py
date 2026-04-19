"""
Acceptance script for ReasoningLayer (Phase 9.5).

10 synthetic query scenarios with known candidate sets and mock Ollama responses.
Verifies: selection correctness, expansion, fallback triggers, token budget.
Attempts a live Ollama round-trip if Ollama is running.
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

from src.models.query import Candidate                     # noqa: E402
from src.reasoning.ollama_client import OllamaClient, OllamaError  # noqa: E402
from src.reasoning.pipeline import ReasoningLayer          # noqa: E402
from src.reasoning.prompt_builder import build_prompt, _CHARS_PER_TOKEN  # noqa: E402


def _cand(page: int, section: str = "chapter 1") -> Candidate:
    return Candidate(
        page_id=f"doc::p{page}", doc_id="doc", source_file="doc.pdf",
        page_number=page, section_path=section,
        bm25_raw=float(20 - page), bm25_normalized=0.9,
    )


def _mock_client(response: str) -> OllamaClient:
    c = MagicMock(spec=OllamaClient)
    c.model = "qwen:7b"
    c.generate.return_value = response
    return c


def _error_client() -> OllamaClient:
    c = MagicMock(spec=OllamaClient)
    c.model = "qwen:7b"
    c.generate.side_effect = OllamaError("connection refused")
    return c


# 10 test scenarios: (description, candidates, page_texts, mock_response, check_fn)
SCENARIOS = [
    (
        "Select pages 1 and 3 from 5-candidate set",
        [_cand(5), _cand(6), _cand(7), _cand(8), _cand(9)],
        {},
        "1, 3",
        lambda r: {5, 7} <= {c.page_number for c in r},
    ),
    (
        "Adjacent page 6 expanded when page 7 selected",
        [_cand(5), _cand(6), _cand(7), _cand(8), _cand(9)],
        {},
        "3",  # page 7
        lambda r: 6 in {c.page_number for c in r} or 8 in {c.page_number for c in r},
    ),
    (
        "Fallback on network error returns top-3",
        [_cand(i) for i in range(1, 6)],
        {},
        None,  # error client
        lambda r: len(r) == 3 and r[0].page_number == 1,
    ),
    (
        "Fallback on unparseable response returns top-3",
        [_cand(i) for i in range(1, 6)],
        {},
        "I cannot determine the answer.",
        lambda r: len(r) == 3,
    ),
    (
        "Result sorted ascending by page_number",
        [_cand(10), _cand(11), _cand(12), _cand(13), _cand(14)],
        {},
        "3, 1",  # reversed order
        lambda r: [c.page_number for c in r] == sorted(c.page_number for c in r),
    ),
    (
        "No duplicates when adjacent to multiple selected pages",
        [_cand(5), _cand(6), _cand(7), _cand(8), _cand(9)],
        {},
        "1, 3",  # pages 5 and 7; page 6 adjacent to both
        lambda r: len([c for c in r if c.page_number == 6]) <= 1,
    ),
    (
        "Out-of-range numbers ignored, no crash",
        [_cand(5), _cand(6), _cand(7)],
        {},
        "1, 50, 100",  # 50 and 100 out of range
        lambda r: 5 in {c.page_number for c in r},
    ),
    (
        "Token budget not exceeded for 8-candidate prompt",
        [_cand(i) for i in range(1, 9)],
        {f"doc::p{i}": f"Page {i} body text about caching and database configuration." for i in range(1, 9)},
        "1",
        lambda r: True,  # just verify no crash; token check done separately
    ),
    (
        "Single candidate selected and returned",
        [_cand(42)],
        {},
        "1",
        lambda r: len(r) == 1 and r[0].page_number == 42,
    ),
    (
        "Empty candidates returns empty",
        [],
        {},
        "1",
        lambda r: r == [],
    ),
]

pass_count = fail_count = 0

print(f"\n{'='*65}")
print("PHASE 9.5 REASONING LAYER ACCEPTANCE TEST")
print(f"{'='*65}\n")

for i, (desc, cands, texts, mock_resp, check) in enumerate(SCENARIOS, 1):
    if mock_resp is None:
        client = _error_client()
    else:
        client = _mock_client(mock_resp)

    layer = ReasoningLayer(client)
    result = layer.select("test query", cands, texts)

    ok = check(result)
    status = "PASS" if ok else "FAIL"
    pages = [c.page_number for c in result]
    if ok:
        pass_count += 1
    else:
        fail_count += 1
    print(f"[{status}] {i:2}. {desc}")
    if not ok:
        print(f"       result pages={pages}")

# Token budget check (scenario 8)
print(f"\n--- Token Budget Check ---")
cands8 = [_cand(i) for i in range(1, 9)]
texts8 = {f"doc::p{i}": f"Page {i} body text about caching and database configuration." for i in range(1, 9)}
prompt, included = build_prompt("What is the caching policy?", cands8, texts8)
tokens = len(prompt) // _CHARS_PER_TOKEN
ok_budget = tokens <= 2000
print(f"  prompt_tokens={tokens} included={included}/8  budget_ok={ok_budget}")
if ok_budget:
    pass_count += 1
else:
    fail_count += 1
    print(f"  [FAIL] token budget exceeded: {tokens} > 2000")

# Live Ollama check
print(f"\n--- Live Ollama Check (optional) ---")
try:
    real_client = OllamaClient(model="qwen:7b", timeout=5)
    test_prompt = "Query: What is caching?\n\nReply with: 1"
    resp = real_client.generate(test_prompt)
    print(f"  Ollama live: OK response={resp[:80]!r}")
except OllamaError as exc:
    print(f"  Ollama live: SKIP (not running) - {exc}")

print(f"\n{'='*65}")
total = pass_count + fail_count
print(f"PASS {pass_count}/{total}  FAIL {fail_count}")
sys.exit(0 if fail_count == 0 else 1)
