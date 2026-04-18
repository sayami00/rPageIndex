from __future__ import annotations

import hashlib
import logging

from whoosh.writing import IndexWriter

from src.assembly.models import PageRecord
from src.features.models import FeatureIndex, FeatureRecord
from src.section_tree.models import SectionTree, TreeNode
from src.tables.models import TableOutput

logger = logging.getLogger(__name__)


# ── section path resolution ────────────────────────────────────────────────────

def _flatten_real_nodes(root: TreeNode) -> list[TreeNode]:
    """Pre-order DFS, skip sentinel root."""
    result: list[TreeNode] = []

    def _dfs(n: TreeNode) -> None:
        if n.depth > 0:
            result.append(n)
        for c in n.children:
            _dfs(c)

    _dfs(root)
    return result


def _build_breadcrumb(node: TreeNode, node_map: dict[str, TreeNode]) -> str:
    """Trace parent_id chain upward to build 'h1 title > h2 title > ...' string."""
    parts: list[str] = []
    current: TreeNode | None = node
    while current and current.depth > 0:
        parts.append(current.title)
        parent_id = current.parent_id
        current = node_map.get(parent_id) if parent_id else None  # type: ignore[arg-type]
    parts.reverse()
    return " > ".join(parts)


def resolve_section(
    page_number: int,
    tree: SectionTree | None,
) -> tuple[str, str]:
    """Return (section_path, node_id) for deepest enclosing section, or ('', '')."""
    if tree is None:
        return ("", "")

    nodes = _flatten_real_nodes(tree.root)
    node_map: dict[str, TreeNode] = {n.node_id: n for n in nodes}
    node_map[tree.root.node_id] = tree.root

    covering = [
        n for n in nodes
        if n.page_spans[0] <= page_number <= n.page_spans[1]
    ]
    if not covering:
        return ("", "")

    deepest = max(covering, key=lambda n: n.depth)
    path = _build_breadcrumb(deepest, node_map)
    return (path, deepest.node_id)


# ── page writer ────────────────────────────────────────────────────────────────

def write_pages(
    writer: IndexWriter,
    records: list[PageRecord],
    tree: SectionTree | None = None,
) -> int:
    count = 0
    for rec in records:
        section_path, _ = resolve_section(rec.page_number, tree)
        writer.add_document(
            page_id=f"{rec.doc_id}::p{rec.page_number}",
            doc_id=rec.doc_id,
            page_number=rec.page_number,
            heading_text=rec.heading_text or "",
            body_text=rec.body_text or "",
            table_text=rec.table_text or "",
            section_path=section_path,
            quality_floor=rec.quality_floor,
        )
        count += 1
    logger.debug("write_pages: %d records written", count)
    return count


# ── section writer ─────────────────────────────────────────────────────────────

def write_sections(writer: IndexWriter, tree: SectionTree) -> int:
    nodes = _flatten_real_nodes(tree.root)
    count = 0
    for node in nodes:
        writer.add_document(
            section_id=node.node_id,
            doc_id=node.doc_id,
            title=node.title or "",
            summary=node.summary or "",
            page_span_first=node.page_spans[0],
            page_span_last=node.page_spans[1],
            depth=node.depth,
            parent_id=node.parent_id or "",
        )
        count += 1
    logger.debug("write_sections: %d nodes written", count)
    return count


# ── feature writer ─────────────────────────────────────────────────────────────

def _feature_id(rec: FeatureRecord) -> str:
    vh = hashlib.sha256(rec.value.encode()).hexdigest()[:8]
    return f"{rec.block_id}::{rec.feature_type}::{vh}"


def write_features(
    writer: IndexWriter,
    feature_index: FeatureIndex,
    tree: SectionTree | None = None,
) -> int:
    count = 0
    for records in feature_index.values():
        for rec in records:
            _, section_node_id = resolve_section(rec.page_number, tree)
            # feature_text: value for most types; for key_value_pair include key
            if rec.key:
                text = f"{rec.key} {rec.value}"
            else:
                text = rec.value

            writer.add_document(
                feature_id=_feature_id(rec),
                doc_id=rec.doc_id,
                feature_type=rec.feature_type,
                feature_text=text,
                feature_exact=rec.value,   # raw, no analysis
                source_page=rec.page_number,
                source_section=section_node_id,
            )
            count += 1
    logger.debug("write_features: %d records written", count)
    return count


# ── table writer ───────────────────────────────────────────────────────────────

def write_tables(writer: IndexWriter, tables: list[TableOutput]) -> int:
    count = 0
    for tbl in tables:
        writer.add_document(
            table_id=tbl.table_id,
            doc_id=tbl.doc_id,
            source_pages=" ".join(str(p) for p in tbl.source_pages),
            headers_text=" ".join(tbl.headers),
            search_rows_text=" ".join(tbl.search_rows),
            continuation_of=tbl.continuation_of or "",
        )
        count += 1
    logger.debug("write_tables: %d records written", count)
    return count
