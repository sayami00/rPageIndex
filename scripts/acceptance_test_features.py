"""
Acceptance test for Phase 6 feature extraction pipeline.

Usage:
    python scripts/acceptance_test_features.py <path_to_document>

Steps:
    1. Parse document → cleanup pipeline → Blocks
    2. Run FeaturePipeline → FeatureIndex
    3. Query each feature type and print samples
    4. Assert: no REJECT block_id appears in any record
    5. Demonstrate heading lookup and key-value lookup
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cleanup.pipeline import CleanupPipeline
from src.features.pipeline import FeaturePipeline
from src.ingestion.dispatcher import DispatcherParser


def _section(title: str) -> None:
    print(f"\n{'=' * 68}")
    print(f"  {title}")
    print(f"{'=' * 68}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/acceptance_test_features.py <document>")
        sys.exit(1)

    doc_path = sys.argv[1]
    if not Path(doc_path).exists():
        print(f"File not found: {doc_path}")
        sys.exit(1)

    print(f"Parsing: {doc_path}")
    raw_blocks = DispatcherParser().parse(doc_path)
    print(f"  {len(raw_blocks)} raw blocks")

    blocks = CleanupPipeline().run(raw_blocks)
    reject_ids = {b.block_id for b in blocks if b.gate_status == "REJECT"}
    print(f"  {len(blocks)} blocks after cleanup  ({len(reject_ids)} REJECT)")

    index = FeaturePipeline().run(blocks)

    # --- Summary ---
    _section("Feature Index Summary")
    for ftype, records in index.items():
        print(f"  {ftype:20s}: {len(records):4d} records")

    # --- Headings ---
    _section("Headings (first 10)")
    for r in index["heading"][:10]:
        print(f"  [p{r.page_number}] {r.value[:80]}")

    # --- Bullet Items ---
    _section("Bullet Items (first 10)")
    for r in index["bullet_item"][:10]:
        print(f"  [p{r.page_number}] {r.value[:80]}")

    # --- Key-Value Pairs ---
    _section("Key-Value Pairs (first 15)")
    for r in index["key_value_pair"][:15]:
        print(f"  key={r.key!r:30s}  value snippet={r.value[:60]!r}")

    # --- Named Entities ---
    _section("Named Entities (grouped by subtype, top 10 each)")
    for subtype in ("ip", "version", "hostname"):
        hits = [r for r in index["named_entity"] if r.entity_subtype == subtype]
        print(f"\n  {subtype.upper()} ({len(hits)} unique):")
        for r in hits[:10]:
            print(f"    {r.value}")

    # --- Repeated Patterns ---
    _section("Repeated Patterns (top 10 by frequency)")
    sorted_rep = sorted(index["repeated_pattern"], key=lambda r: r.frequency or 0, reverse=True)
    for r in sorted_rep[:10]:
        print(f"  freq={r.frequency:3d}  {r.value}")

    # --- Assertion: no REJECT block in any record ---
    _section("Validation")
    all_records = [r for records in index.values() for r in records]
    violations = [r for r in all_records if r.block_id in reject_ids]
    if violations:
        print(f"  [FAIL] {len(violations)} records reference REJECT blocks:")
        for v in violations[:5]:
            print(f"    {v.block_id} — {v.feature_type}: {v.value[:50]!r}")
    else:
        print(f"  [PASS] No REJECT block references found ({len(all_records)} records checked)")

    # --- Lookup demo ---
    if index["heading"]:
        _section("Lookup Demo: find heading by substring")
        sample_heading = index["heading"][0].value
        word = sample_heading.split()[0] if sample_heading.split() else ""
        hits = [r for r in index["heading"] if word.lower() in r.value.lower()]
        print(f"  Query word: {word!r}  → {len(hits)} hit(s)")
        for r in hits[:3]:
            print(f"    {r.value}")

    if index["key_value_pair"]:
        _section("Lookup Demo: find key-value by key substring")
        sample_key = index["key_value_pair"][0].key or ""
        hits = [r for r in index["key_value_pair"] if sample_key.lower() in (r.key or "").lower()]
        print(f"  Query key: {sample_key!r}  → {len(hits)} hit(s)")
        for r in hits[:3]:
            print(f"    key={r.key!r}  value={r.value[:60]!r}")

    print("\nDone.")


if __name__ == "__main__":
    main()
