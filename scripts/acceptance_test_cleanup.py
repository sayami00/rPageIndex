"""
Acceptance test for Phase 4 cleanup pipeline.

Usage:
    python scripts/acceptance_test_cleanup.py <path_to_document>

Runs the cleanup pipeline on up to 100 blocks from the given document,
then prints 20 random samples from each gate bucket (REJECT / FLAG / PASS)
for manual inspection.

Adjust thresholds in src/cleanup/quality.py if the distribution looks wrong:
    - REJECT blocks should look like garbage or boilerplate
    - FLAG blocks should look like partial or degraded content
    - PASS blocks should look clean and complete
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cleanup.pipeline import CleanupPipeline
from src.ingestion.dispatcher import DispatcherParser


_SAMPLE_SIZE = 20
_MAX_BLOCKS = 100


def _print_separator(title: str) -> None:
    width = 72
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_block(i: int, block) -> None:
    print(f"\n[{i+1}] block_id={block.block_id}")
    print(f"     type={block.block_type}  score={block.quality_score:.3f}"
          f"  boilerplate={block.is_boilerplate}  duplicate={block.is_duplicate}")
    text = block.clean_text[:300].replace("\n", " ")
    if len(block.clean_text) > 300:
        text += " ..."
    print(f"     text: {text!r}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/acceptance_test_cleanup.py <path_to_document>")
        sys.exit(1)

    doc_path = sys.argv[1]
    if not Path(doc_path).exists():
        print(f"File not found: {doc_path}")
        sys.exit(1)

    print(f"Parsing: {doc_path}")
    parser = DispatcherParser()
    raw_blocks = parser.parse(doc_path)

    if not raw_blocks:
        print("No blocks extracted from document.")
        sys.exit(1)

    if len(raw_blocks) > _MAX_BLOCKS:
        raw_blocks = raw_blocks[:_MAX_BLOCKS]

    print(f"Extracted {len(raw_blocks)} raw blocks. Running cleanup pipeline...")

    pipeline = CleanupPipeline()
    blocks = pipeline.run(raw_blocks)

    by_gate: dict[str, list] = {"REJECT": [], "FLAG": [], "PASS": []}
    for b in blocks:
        by_gate[b.gate_status].append(b)

    total = len(blocks)
    print(f"\nResults: {total} blocks after cleanup")
    for gate, group in by_gate.items():
        pct = len(group) / total * 100 if total else 0
        print(f"  {gate:6s}: {len(group):4d}  ({pct:.1f}%)")

    for gate in ("REJECT", "FLAG", "PASS"):
        group = by_gate[gate]
        sample = random.sample(group, min(_SAMPLE_SIZE, len(group)))
        _print_separator(f"{gate} — {len(sample)} of {len(group)} sampled")
        if not sample:
            print("  (no blocks in this bucket)")
            continue
        for i, b in enumerate(sample):
            _print_block(i, b)

    print("\n\nInspect the samples above.")
    print("If REJECT blocks contain useful content → lower _REJECT_THRESHOLD in quality.py")
    print("If PASS blocks look degraded → raise _FLAG_THRESHOLD in quality.py")


if __name__ == "__main__":
    main()
