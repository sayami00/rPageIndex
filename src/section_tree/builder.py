from __future__ import annotations

from src.models.ingestion import Block
from src.section_tree.models import SectionTree, TreeNode

_LEVEL: dict[str, int] = {"heading_1": 1, "heading_2": 2, "heading_3": 3}


def build_tree(
    headings: list[Block],
    doc_id: str,
    source_file: str,
    total_pages: int,
) -> SectionTree:
    root = TreeNode(
        node_id=f"{doc_id}::root",
        doc_id=doc_id,
        title="__root__",
        block_id="",
        heading_level=0,
        depth=0,
        parent_id=None,
        page_spans=(1, total_pages),
    )

    if not headings:
        return SectionTree(
            doc_id=doc_id,
            source_file=source_file,
            root=root,
            total_pages=total_pages,
        )

    # Stack-based hierarchy assignment — root is always base
    stack: list[TreeNode] = [root]

    for block in headings:
        level = _LEVEL[block.block_type]
        node = TreeNode(
            node_id=f"{doc_id}::h{level}::{block.block_id}",
            doc_id=doc_id,
            title=block.clean_text.strip(),
            block_id=block.block_id,
            heading_level=level,
            depth=level,
            parent_id=None,
            page_spans=(block.page_number, block.page_number),  # start placeholder
        )

        # Pop until top has lower level (root at depth 0 never popped)
        while len(stack) > 1 and stack[-1].heading_level >= level:
            stack.pop()

        parent = stack[-1]
        node.parent_id = parent.node_id
        parent.children.append(node)
        stack.append(node)

    # Second pass: assign accurate page spans
    flat = _flatten_nodes(root)
    _assign_page_spans(flat, total_pages)

    return SectionTree(
        doc_id=doc_id,
        source_file=source_file,
        root=root,
        total_pages=total_pages,
    )


def _flatten_nodes(root: TreeNode) -> list[TreeNode]:
    """Pre-order DFS of all real nodes (excludes root sentinel)."""
    result: list[TreeNode] = []

    def _dfs(node: TreeNode) -> None:
        if node.depth > 0:
            result.append(node)
        for child in node.children:
            _dfs(child)

    _dfs(root)
    return result


def _assign_page_spans(nodes: list[TreeNode], total_pages: int) -> None:
    """For each node, end page = page before next same-or-higher-level node, or total_pages."""
    for i, node in enumerate(nodes):
        start = node.page_spans[0]
        end = total_pages
        for j in range(i + 1, len(nodes)):
            if nodes[j].heading_level <= node.heading_level:
                end = max(start, nodes[j].page_spans[0] - 1)
                break
        node.page_spans = (start, end)
