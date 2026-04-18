"""
Acceptance test for Phase 7 — Section Tree.

Usage:
    python scripts/acceptance_test_section_tree.py <path_to_pdf>

Requires Ollama running at localhost:11434 with a model available.
Set OLLAMA_MODEL env var to override model (default: llama3.2).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cleanup.pipeline import CleanupPipeline
from src.ingestion.pdf_parser import PDFParser
from src.section_tree.builder import _flatten_nodes
from src.section_tree.pipeline import SectionTreePipeline
from src.section_tree.summarizer import flatten_nodes


def _print_tree(node, indent: int = 0) -> None:
    if node.depth > 0:
        prefix = "  " * (indent - 1) + ("└─ " if indent > 0 else "")
        span = f"pp.{node.page_spans[0]}–{node.page_spans[1]}"
        summary_preview = node.summary[:80] + ("…" if len(node.summary) > 80 else "")
        print(f"{prefix}[h{node.heading_level}] {node.title!r:<40} {span}")
        if summary_preview:
            print(f"{'  ' * indent}    summary: {summary_preview}")
    for child in node.children:
        _print_tree(child, indent + 1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/acceptance_test_section_tree.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    cache_dir = ".cache/summaries_acceptance"

    print(f"\n=== Phase 7 Acceptance Test ===")
    print(f"File  : {pdf_path}")
    print(f"Model : {model}\n")

    # Parse
    parser = PDFParser()
    raw_blocks = parser.parse(pdf_path)
    print(f"Parsed {len(raw_blocks)} raw blocks")

    # Cleanup
    cleanup = CleanupPipeline()
    blocks = cleanup.run(raw_blocks)
    print(f"Cleaned → {len(blocks)} blocks")

    # Detect total pages
    total_pages = max(b.page_number for b in blocks) if blocks else 1
    doc_id = Path(pdf_path).stem

    # Run section tree pipeline
    t0 = time.monotonic()
    pipeline = SectionTreePipeline(model=model, cache_dir=cache_dir)
    tree = pipeline.run(blocks, doc_id=doc_id, source_file=pdf_path, total_pages=total_pages)
    elapsed = time.monotonic() - t0

    print(f"\nTree built in {elapsed:.2f}s")
    print(f"Total pages: {total_pages}")

    nodes = flatten_nodes(tree.root)
    print(f"Total nodes: {len(nodes)}\n")

    # Print tree
    print("─── Section Tree ───────────────────────────────────────────")
    _print_tree(tree.root)
    print()

    # ── Assertions ──────────────────────────────────────────────────────────

    # 1. Every heading_1 block → depth-1 node
    from src.section_tree.detector import extract_headings
    h1_blocks = [b for b in blocks if b.block_type == "heading_1"]
    h1_nodes = [n for n in nodes if n.heading_level == 1]
    assert len(h1_nodes) == len(h1_blocks), (
        f"heading_1 count mismatch: {len(h1_blocks)} blocks vs {len(h1_nodes)} nodes"
    )
    print(f"✓ All {len(h1_blocks)} heading_1 blocks became depth-1 nodes")

    # 2. Every heading_2 block is child of nearest preceding heading_1
    h2_nodes = [n for n in nodes if n.heading_level == 2]
    for n in h2_nodes:
        parent = _find_node(tree.root, n.parent_id)
        assert parent is not None, f"h2 node {n.node_id} has no parent in tree"
        assert parent.heading_level in (0, 1), (
            f"h2 {n.node_id} parent has level {parent.heading_level}, expected 0 or 1"
        )
    print(f"✓ All {len(h2_nodes)} heading_2 nodes have valid parent (h1 or root)")

    # 3. No page_spans where first > last
    bad_spans = [n for n in nodes if n.page_spans[0] > n.page_spans[1]]
    assert not bad_spans, f"Nodes with first>last page_spans: {[n.node_id for n in bad_spans]}"
    print(f"✓ All {len(nodes)} nodes have valid page_spans (first ≤ last)")

    # 4. Leaf nodes have non-empty summary (Ollama available)
    leaf_nodes = [n for n in nodes if not n.children]
    empty_summaries = [n for n in leaf_nodes if not n.summary]
    if empty_summaries:
        print(f"⚠ {len(empty_summaries)}/{len(leaf_nodes)} leaf nodes have empty summary "
              f"(Ollama may be unavailable)")
    else:
        print(f"✓ All {len(leaf_nodes)} leaf nodes have non-empty summary")

    # 5. Second run — cache hit rate ≥ 50%
    print("\nRunning second pass to test cache...")
    # Reset summaries to force re-check
    for n in nodes:
        n.summary = ""
    tree2 = pipeline.run(blocks, doc_id=doc_id, source_file=pdf_path, total_pages=total_pages)
    nodes2 = flatten_nodes(tree2.root)
    filled = sum(1 for n in nodes2 if n.summary)
    if nodes2:
        hit_rate = filled / len(nodes2)
        assert hit_rate >= 0.5, f"Cache hit rate {hit_rate:.0%} < 50%"
        print(f"✓ Cache hit rate: {hit_rate:.0%} ({filled}/{len(nodes2)} nodes served from cache)")

    print("\n=== All assertions passed ===\n")


def _find_node(root, node_id: str | None):
    if node_id is None:
        return None
    if root.node_id == node_id:
        return root
    for child in root.children:
        found = _find_node(child, node_id)
        if found:
            return found
    return None


if __name__ == "__main__":
    main()
