from __future__ import annotations

import logging

from src.models.ingestion import Block
from src.tables.detector import filter_table_blocks
from src.tables.header import detect_header, parse_table_text
from src.tables.linker import build_table_outputs
from src.tables.models import TableOutput
from src.tables.multi_page import group_continuations
from src.tables.normalizer import normalize_rows

logger = logging.getLogger(__name__)


class TablePipeline:
    """Transform a list of Blocks into structured TableOutput objects.

    Step order (strict):
        1. Filter: keep non-REJECT table blocks, drop pseudo-tables
        2. Parse: clean_text → raw rows
        3. Header detection: first row vs synthetic
        4. Normalize: cell whitespace, empty cells, merged cell fill
        5. Group: multi-page continuation detection
        6. Link: assign IDs, merge pages, serialize rows
    """

    def run(self, blocks: list[Block]) -> list[TableOutput]:
        # Steps 1–4: per block
        table_data: list[dict] = []
        for block in filter_table_blocks(blocks):
            item = self._process_block(block)
            if item is not None:
                table_data.append(item)

        if not table_data:
            return []

        # Sort by (doc_id, page_number, sequence) for multi-page grouping
        table_data.sort(key=lambda x: (
            x["block"].doc_id,
            x["block"].page_number,
            x["block"].sequence,
        ))

        # Step 5: group continuations
        groups = group_continuations(table_data)

        # Step 6: build outputs
        return build_table_outputs(groups)

    def _process_block(self, block: Block) -> dict | None:
        rows = parse_table_text(block.clean_text)
        if not rows:
            logger.debug("Block %s: empty parse result, skipping", block.block_id)
            return None

        headers, data_rows = detect_header(rows)
        if not headers:
            logger.debug("Block %s: no headers detected, skipping", block.block_id)
            return None

        structured = normalize_rows(headers, data_rows)
        if not structured:
            logger.debug("Block %s: no data rows after normalization, skipping", block.block_id)
            return None

        return {
            "block": block,
            "headers": headers,
            "structured": structured,
        }
