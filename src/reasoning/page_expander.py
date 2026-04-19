from __future__ import annotations

from src.models.query import Candidate
from src.section_tree.models import SectionTree


def expand_pages(
    selected: list[Candidate],
    all_candidates: list[Candidate],
    tree: SectionTree | None = None,
) -> list[Candidate]:
    """
    For each selected candidate, add adjacent candidates (page_number ±1, same section)
    from all_candidates that were not already selected.
    Returns merged list deduped by page_id, sorted by page_number.
    """
    selected_ids: set[str] = {c.page_id for c in selected}
    result: list[Candidate] = list(selected)

    # Build lookup: page_number → candidate
    by_page: dict[int, Candidate] = {c.page_number: c for c in all_candidates}

    for sel in selected:
        for offset in (-1, 1):
            neighbour_page = sel.page_number + offset
            neighbour = by_page.get(neighbour_page)
            if neighbour is None:
                continue
            if neighbour.page_id in selected_ids:
                continue
            if not _same_section(sel, neighbour, tree):
                continue
            selected_ids.add(neighbour.page_id)
            result.append(neighbour)

    result.sort(key=lambda c: c.page_number)
    return result


def _same_section(a: Candidate, b: Candidate, tree: SectionTree | None) -> bool:
    if tree is not None:
        section_a = _find_deepest_section(a.page_number, tree)
        section_b = _find_deepest_section(b.page_number, tree)
        if section_a is not None and section_b is not None:
            return section_a.node_id == section_b.node_id
    # Fall back to section_path string comparison
    return bool(a.section_path) and a.section_path == b.section_path


def _find_deepest_section(page_number: int, tree: SectionTree):
    """Return deepest TreeNode whose page_spans contains page_number."""
    best = None

    def _dfs(node):
        nonlocal best
        if node.depth > 0:
            first, last = node.page_spans
            if first <= page_number <= last:
                if best is None or node.depth > best.depth:
                    best = node
        for child in node.children:
            _dfs(child)

    _dfs(tree.root)
    return best
