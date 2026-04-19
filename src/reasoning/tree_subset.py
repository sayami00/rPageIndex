from __future__ import annotations

from src.models.query import Candidate
from src.section_tree.models import SectionTree, TreeNode


def build_tree_subset(candidates: list[Candidate], tree: SectionTree) -> list[TreeNode]:
    """
    Return TreeNodes whose page_spans overlap with any candidate page.
    Pre-order DFS, skips root sentinel. Deduped, preserves document order.
    """
    candidate_pages: set[int] = {c.page_number for c in candidates}
    result: list[TreeNode] = []

    def _dfs(node: TreeNode) -> None:
        if node.depth > 0:
            first, last = node.page_spans
            if any(first <= p <= last for p in candidate_pages):
                result.append(node)
        for child in node.children:
            _dfs(child)

    _dfs(tree.root)
    return result
