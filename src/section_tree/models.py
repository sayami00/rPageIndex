from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    node_id: str           # "{doc_id}::h{level}::{block_id}" or "{doc_id}::root"
    doc_id: str
    title: str             # clean_text of the heading block
    block_id: str          # originating Block.block_id (empty for root)
    heading_level: int     # 0=root, 1=h1, 2=h2, 3=h3
    depth: int             # same as heading_level
    parent_id: str | None  # None for root only
    children: list[TreeNode] = field(default_factory=list)
    page_spans: tuple[int, int] = (0, 0)   # (first_page, last_page) inclusive
    summary: str = ""


@dataclass
class SectionTree:
    doc_id: str
    source_file: str
    root: TreeNode         # sentinel root (depth=0, title="__root__")
    total_pages: int
