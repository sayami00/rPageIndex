"""
Acceptance test for Phase 7 page assembly pipeline.

Usage:
    python scripts/acceptance_test_assembly.py <path_to_document>

Steps:
    1. Parse → cleanup → table pipeline → feature pipeline → assembly pipeline
    2. Sample 3 page records, print composite fields
    3. Assert: every PASS/FLAG paragraph block on sampled pages appears in body_text
    4. Assert: every heading block on sampled pages appears in heading_text
    5. Assert: quality_floor matches lowest quality_score for each sampled page
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.assembly.pipeline import AssemblyPipeline
from src.cleanup.pipeline import CleanupPipeline
from src.features.pipeline import FeaturePipeline
from src.ingestion.dispatcher import DispatcherParser
from src.tables.pipeline import TablePipeline


_HEADING_TYPES = frozenset({"heading_1", "heading_2", "heading_3"})


def _sep(title: str = "") -> None:
    print(f"\n{'=' * 70}")
    if title:
        print(f"  {title}")
        print(f"{'=' * 70}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/acceptance_test_assembly.py <document>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Parsing: {path}")
    raw_blocks = DispatcherParser().parse(path)
    print(f"  {len(raw_blocks)} raw blocks")

    blocks = CleanupPipeline().run(raw_blocks)
    print(f"  {len(blocks)} blocks after cleanup")

    tables = TablePipeline().run(blocks)
    print(f"  {len(tables)} tables")

    feature_index = FeaturePipeline().run(blocks)
    total_features = sum(len(v) for v in feature_index.values())
    print(f"  {total_features} feature records")

    page_records = AssemblyPipeline().run(blocks, feature_index, tables)
    print(f"  {len(page_records)} page records")

    if not page_records:
        print("No page records produced.")
        sys.exit(0)

    # Build page→blocks lookup for assertions
    from collections import defaultdict
    page_blocks_map = defaultdict(list)
    for b in blocks:
        page_blocks_map[(b.doc_id, b.page_number)].append(b)

    # Sample up to 3 pages
    sample = random.sample(page_records, min(3, len(page_records)))

    _sep("Page Assembly — 3 Sampled Pages")

    failures: list[str] = []

    for rec in sample:
        _sep(f"Page {rec.page_number}  |  doc={rec.doc_id}")
        print(f"  block_count   : {rec.block_count}")
        print(f"  quality_floor : {rec.quality_floor}")
        print(f"  features      : {len(rec.features)}")
        print(f"  tables        : {len(rec.tables)}")
        print(f"  heading_text  : {rec.heading_text[:120]!r}")
        print(f"  body_text     : {rec.body_text[:200]!r}")
        print(f"  table_text    : {rec.table_text[:200]!r}")

        page_key = (rec.doc_id, rec.page_number)
        page_blks = page_blocks_map[page_key]

        # Assert: all heading blocks appear in heading_text
        for b in page_blks:
            if b.block_type in _HEADING_TYPES:
                if b.clean_text.strip() not in rec.heading_text:
                    failures.append(
                        f"Page {rec.page_number}: heading block {b.block_id!r} "
                        f"missing from heading_text"
                    )

        # Assert: all PASS/FLAG paragraphs appear in body_text
        for b in page_blks:
            if b.block_type == "paragraph" and b.gate_status in ("PASS", "FLAG"):
                if b.clean_text.strip() not in rec.body_text:
                    failures.append(
                        f"Page {rec.page_number}: paragraph block {b.block_id!r} "
                        f"(gate={b.gate_status}) missing from body_text"
                    )

        # Assert: quality_floor matches minimum
        if page_blks:
            expected_floor = round(min(b.quality_score for b in page_blks), 4)
            if abs(rec.quality_floor - expected_floor) > 1e-6:
                failures.append(
                    f"Page {rec.page_number}: quality_floor={rec.quality_floor} "
                    f"expected {expected_floor}"
                )

    _sep("Validation")
    if failures:
        print(f"  [FAIL] {len(failures)} assertion(s) failed:")
        for f in failures:
            print(f"    {f}")
    else:
        print(f"  [PASS] All assertions passed on {len(sample)} sampled pages")

    print("\nDone.")


if __name__ == "__main__":
    main()
