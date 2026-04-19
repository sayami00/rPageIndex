"""Acceptance test runner for QueryRouter — prints per-query results and summary."""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

from src.query.router import QueryRouter  # noqa: E402
from tests.query.test_router import CASES  # noqa: E402

router = QueryRouter()

pass_count = 0
fail_count = 0
rows: list[str] = []

for query, exp_type, exp_index, exp_priority in CASES:
    result = router.classify(query)
    ok = (
        result.query_type == exp_type
        and result.target_index == exp_index
        and result.matched_priority == exp_priority
    )
    status = "PASS" if ok else "FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1
    rows.append(
        f"[{status}] P{result.matched_priority} {result.query_type:<16} "
        f"rule={result.matched_rule:<20} query={query!r}"
    )
    if not ok:
        rows.append(
            f"       expected P{exp_priority} {exp_type} / {exp_index}"
        )

print("\n".join(rows))
total = pass_count + fail_count
accuracy = pass_count / total * 100
print(f"\n{'='*60}")
print(f"PASS {pass_count}/{total}  ({accuracy:.1f}%)  FAIL {fail_count}")
target = 85.0
print(f"Target: {target}%  — {'MET' if accuracy >= target else 'NOT MET'}")
sys.exit(0 if accuracy >= target else 1)
