from __future__ import annotations

import logging

from src.cleanup.boilerplate import is_boilerplate as detect_boilerplate
from src.cleanup.classifier import classify_block
from src.cleanup.deduplication import mark_duplicates
from src.cleanup.list_cleanup import normalize_list_item
from src.cleanup.ocr_cleanup import fix_ocr_text
from src.cleanup.paragraph import reconstruct_paragraphs
from src.cleanup.quality import compute_gate_status, compute_quality_score
from src.cleanup.search_normalizer import build_search_text
from src.cleanup.table_cleanup import normalize_headers, normalize_table_rows
from src.cleanup.whitespace import clean_whitespace
from src.models.ingestion import Block, RawBlock

logger = logging.getLogger(__name__)


class CleanupPipeline:
    """Transform a list of RawBlocks into cleaned, classified, gated Blocks.

    Strict execution order per spec:
        steps 1–9: per-block transformations
        step 10:   deduplication across all blocks in the batch
        steps 11–12: quality scoring and gate assignment per block
    """

    def run(self, blocks: list[RawBlock]) -> list[Block]:
        intermediates: list[dict] = []
        for raw in blocks:
            inter = self._process_single(raw)
            if inter is not None:
                intermediates.append(inter)

        # Step 10: cross-block deduplication
        mark_duplicates(intermediates)

        # Steps 11–12: quality score + gate
        return [self._finalize(inter) for inter in intermediates]

    def _process_single(self, raw: RawBlock) -> dict | None:
        # Steps 1–2: whitespace cleanup
        clean = clean_whitespace(raw.raw_text)
        if clean is None:
            logger.debug("Block %s dropped: too short after whitespace cleanup", raw.block_id)
            return None

        # Step 3: boilerplate detection
        boilerplate = detect_boilerplate(clean)

        # Step 4: paragraph reconstruction
        clean = reconstruct_paragraphs(clean)

        # Step 8: OCR cleanup (before classification — improves text quality)
        if raw.source_format == "ocr":
            clean = fix_ocr_text(clean)

        # Step 5: block classification
        block_type = classify_block(clean, type_hint=raw.block_type_hint)

        # Step 6: list normalization
        if block_type == "list_item":
            clean, _ = normalize_list_item(clean)

        # Step 7: table normalization
        raw_rows = raw.raw_rows
        raw_headers = raw.raw_headers
        if block_type == "table" and raw_rows:
            raw_rows = normalize_table_rows(raw_rows)
            if raw_headers:
                raw_headers = normalize_headers(raw_headers)

        # Step 9: build search_text
        search = build_search_text(clean)

        return {
            "block_id": raw.block_id,
            "doc_id": raw.doc_id,
            "source_file": raw.source_file,
            "page_number": raw.page_number,
            "sequence": raw.sequence,
            "clean_text": clean,
            "search_text": search,
            "block_type": block_type,
            "is_boilerplate": boilerplate,
            "is_duplicate": False,
            "duplicate_of": None,
        }

    def _finalize(self, inter: dict) -> Block:
        score = compute_quality_score(inter["clean_text"], inter["is_boilerplate"])
        gate = compute_gate_status(score)

        return Block(
            block_id=inter["block_id"],
            doc_id=inter["doc_id"],
            source_file=inter["source_file"],
            page_number=inter["page_number"],
            sequence=inter["sequence"],
            clean_text=inter["clean_text"],
            search_text=inter["search_text"],
            block_type=inter["block_type"],
            quality_score=score,
            gate_status=gate,
            should_index=gate != "REJECT",
            low_confidence=gate == "FLAG",
            is_boilerplate=inter["is_boilerplate"],
            is_duplicate=inter["is_duplicate"],
            duplicate_of=inter["duplicate_of"],
        )
