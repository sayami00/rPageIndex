from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from src.assembly.models import PageRecord
from src.bm25.indexer import delete_by_doc, doc_count, get_writer, open_or_create
from src.bm25.metadata import IndexMetadata
from src.bm25.schemas import feature_schema, page_schema, section_schema, table_schema
from src.bm25.writers import write_features, write_pages, write_sections, write_tables
from src.features.models import FeatureIndex
from src.section_tree.models import SectionTree
from src.tables.models import TableOutput

logger = logging.getLogger(__name__)


class IndexPipeline:
    def __init__(self, index_root: str = ".index/"):
        self._root = index_root
        Path(index_root).mkdir(parents=True, exist_ok=True)

    def build(
        self,
        records: list[PageRecord],
        trees: list[SectionTree],
        feature_indices: list[FeatureIndex],
        tables: list[TableOutput],
        source_files: dict[str, str],    # doc_id → absolute file path
        force: bool = False,
    ) -> dict:
        meta = IndexMetadata(self._root)

        # Open all four indices
        page_idx = open_or_create(self._root, "page", page_schema)
        section_idx = open_or_create(self._root, "section", section_schema)
        feature_idx = open_or_create(self._root, "feature", feature_schema)
        table_idx = open_or_create(self._root, "table", table_schema)

        # Determine which doc_ids are stale/new
        doc_hashes: dict[str, str] = {}
        for doc_id, path in source_files.items():
            try:
                doc_hashes[doc_id] = IndexMetadata.file_hash(path)
            except Exception:
                doc_hashes[doc_id] = ""

        changed_docs: set[str] = set()
        for doc_id, h in doc_hashes.items():
            if force or meta.is_changed(doc_id, h):
                changed_docs.add(doc_id)

        if not changed_docs:
            logger.info("IndexPipeline: all docs unchanged, skipping re-index")
            return meta.all_stats()

        logger.info("IndexPipeline: re-indexing %d changed doc(s): %s", len(changed_docs), changed_docs)

        # Group inputs by doc_id
        pages_by_doc: dict[str, list[PageRecord]] = defaultdict(list)
        for rec in records:
            pages_by_doc[rec.doc_id].append(rec)

        tree_by_doc: dict[str, SectionTree] = {t.doc_id: t for t in trees}
        tables_by_doc: dict[str, list[TableOutput]] = defaultdict(list)
        for tbl in tables:
            tables_by_doc[tbl.doc_id].append(tbl)

        # Merge feature indices by doc_id
        features_by_doc: dict[str, FeatureIndex] = {}
        for fi in feature_indices:
            for ftype, recs in fi.items():
                for rec in recs:
                    if rec.doc_id not in features_by_doc:
                        features_by_doc[rec.doc_id] = {}
                    features_by_doc[rec.doc_id].setdefault(ftype, []).append(rec)

        # Open writers
        pw = get_writer(page_idx)
        sw = get_writer(section_idx)
        fw = get_writer(feature_idx)
        tw = get_writer(table_idx)

        page_count = section_count = feature_count = table_count = 0

        for doc_id in changed_docs:
            # Delete stale records from all indices
            delete_by_doc(pw, doc_id)
            delete_by_doc(sw, doc_id)
            delete_by_doc(fw, doc_id)
            delete_by_doc(tw, doc_id)

            tree = tree_by_doc.get(doc_id)

            page_count += write_pages(pw, pages_by_doc.get(doc_id, []), tree)
            if tree:
                section_count += write_sections(sw, tree)
            feature_count += write_features(fw, features_by_doc.get(doc_id, {}), tree)
            table_count += write_tables(tw, tables_by_doc.get(doc_id, []))

            meta.record_document(doc_id, source_files.get(doc_id, ""), doc_hashes[doc_id])

        # Commit all writers
        pw.commit()
        sw.commit()
        fw.commit()
        tw.commit()

        # Update metadata stats
        meta.record_index_build("page", doc_count(page_idx), page_count)
        meta.record_index_build("section", doc_count(section_idx), section_count)
        meta.record_index_build("feature", doc_count(feature_idx), feature_count)
        meta.record_index_build("table", doc_count(table_idx), table_count)
        meta.save()

        logger.info(
            "IndexPipeline: pages=%d sections=%d features=%d tables=%d",
            page_count, section_count, feature_count, table_count,
        )
        return meta.all_stats()

    def rebuild(
        self,
        records: list[PageRecord],
        trees: list[SectionTree],
        feature_indices: list[FeatureIndex],
        tables: list[TableOutput],
        source_files: dict[str, str],
    ) -> dict:
        return self.build(records, trees, feature_indices, tables, source_files, force=True)
