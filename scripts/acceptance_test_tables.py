"""
Acceptance test for Phase 5 table intelligence pipeline.

Usage:
    python scripts/acceptance_test_tables.py <path_to_document>

Steps:
    1. Parse document → RawBlocks
    2. Run cleanup pipeline → Blocks
    3. Run table pipeline → TableOutputs (up to 5 tables)
    4. Print search_rows for each table
    5. Verify every header token appears in every row sentence
    6. Run BM25 query for a user-supplied value to confirm retrieval

    python scripts/acceptance_test_tables.py doc.pdf --query "10.0.0.1"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cleanup.pipeline import CleanupPipeline
from src.ingestion.dispatcher import DispatcherParser
from src.tables.pipeline import TablePipeline


def _verify_headers_in_rows(table) -> list[str]:
    """Return list of violations: rows missing any header token."""
    violations = []
    for i, sentence in enumerate(table.search_rows):
        for col in table.headers:
            if col and col not in sentence:
                violations.append(f"  row {i}: missing column '{col}' — {sentence[:80]!r}")
    return violations


def _bm25_search(search_rows: list[str], query: str) -> list[tuple[int, float, str]]:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("  [rank_bm25 not installed — skipping BM25 check]")
        print("  Install: uv pip install rank-bm25")
        return []

    tokenized = [row.lower().split() for row in search_rows]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(i, score, search_rows[i]) for i, score in ranked[:5] if score > 0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", help="Path to document file")
    parser.add_argument("--query", default="", help="BM25 query string to test retrieval")
    args = parser.parse_args()

    if not Path(args.document).exists():
        print(f"File not found: {args.document}")
        sys.exit(1)

    print(f"Parsing: {args.document}")
    raw_blocks = DispatcherParser().parse(args.document)
    print(f"  {len(raw_blocks)} raw blocks extracted")

    print("Running cleanup pipeline...")
    blocks = CleanupPipeline().run(raw_blocks)
    table_blocks = [b for b in blocks if b.block_type == "table"]
    print(f"  {len(blocks)} blocks after cleanup, {len(table_blocks)} are tables")

    print("Running table pipeline...")
    tables = TablePipeline().run(blocks)
    print(f"  {len(tables)} logical tables produced")

    if not tables:
        print("No tables found. Try a different document.")
        sys.exit(0)

    # Show up to 5 tables
    for idx, table in enumerate(tables[:5]):
        width = 72
        print(f"\n{'=' * width}")
        print(f"  Table {idx + 1}: {table.table_id}")
        print(f"  Pages: {table.source_pages}  |  Headers: {table.headers}")
        print(f"  Rows: {len(table.structured)}  |  search_rows: {len(table.search_rows)}")
        print(f"{'=' * width}")

        # Print first 3 search_rows
        for i, row_sentence in enumerate(table.search_rows[:3]):
            print(f"  [{i}] {row_sentence}")
        if len(table.search_rows) > 3:
            print(f"  ... ({len(table.search_rows) - 3} more rows)")

        # Verify headers appear in rows
        violations = _verify_headers_in_rows(table)
        if violations:
            print(f"\n  [FAIL] Header token violations ({len(violations)}):")
            for v in violations[:5]:
                print(v)
        else:
            print(f"\n  [PASS] All header tokens present in all row sentences")

        # BM25 search
        if args.query and table.search_rows:
            print(f"\n  BM25 query: {args.query!r}")
            hits = _bm25_search(table.search_rows, args.query)
            if hits:
                for rank, (row_idx, score, sentence) in enumerate(hits):
                    print(f"    #{rank + 1} row {row_idx} score={score:.3f}: {sentence[:100]!r}")
            else:
                print("    No hits above threshold.")

    print(f"\nDone. Inspect output above for correctness.")
    print("If header tokens are missing from rows → check serializer.py")
    print("If tables not detected → check detector.py pseudo-table heuristic")


if __name__ == "__main__":
    main()
