from __future__ import annotations

import logging
from collections import defaultdict

from src.assembly.assembler import build_page_record
from src.assembly.models import PageRecord
from src.features.models import FeatureIndex, FeatureRecord
from src.models.ingestion import Block

logger = logging.getLogger(__name__)


class AssemblyPipeline:
    """Aggregate cleaned blocks, features, and tables into per-page PageRecords.

    Inputs:
        blocks        — list[Block] from CleanupPipeline
        feature_index — FeatureIndex from FeaturePipeline
        tables        — list[TableOutput] from TablePipeline

    Output:
        list[PageRecord] sorted by (doc_id, page_number)
    """

    def run(
        self,
        blocks: list[Block],
        feature_index: FeatureIndex,
        tables: list,  # list[TableOutput]
    ) -> list[PageRecord]:
        if not blocks:
            return []

        # Flatten FeatureIndex → list[FeatureRecord]
        all_features: list[FeatureRecord] = [
            record
            for records in feature_index.values()
            for record in records
        ]

        # Group blocks by (doc_id, page_number)
        page_map: dict[tuple[str, int], list[Block]] = defaultdict(list)
        source_file_map: dict[tuple[str, int], str] = {}
        for b in blocks:
            key = (b.doc_id, b.page_number)
            page_map[key].append(b)
            source_file_map[key] = b.source_file

        # Build one PageRecord per page, sorted
        records: list[PageRecord] = []
        for (doc_id, page_number) in sorted(page_map.keys()):
            page_blocks = page_map[(doc_id, page_number)]
            source_file = source_file_map[(doc_id, page_number)]
            record = build_page_record(
                doc_id=doc_id,
                source_file=source_file,
                page_number=page_number,
                page_blocks=page_blocks,
                all_features=all_features,
                all_tables=tables,
            )
            records.append(record)

        logger.debug(
            "AssemblyPipeline: %d blocks → %d page records", len(blocks), len(records)
        )
        return records
