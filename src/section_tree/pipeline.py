from __future__ import annotations

import asyncio
import logging

from src.models.ingestion import Block
from src.section_tree.builder import build_tree
from src.section_tree.cache import SummaryCache
from src.section_tree.detector import extract_headings
from src.section_tree.models import SectionTree, TreeNode
from src.section_tree.summarizer import flatten_nodes, generate_summaries

logger = logging.getLogger(__name__)


class SectionTreePipeline:
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        cache_dir: str = ".cache/summaries",
        max_concurrent: int = 5,
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.cache_dir = cache_dir
        self.max_concurrent = max_concurrent

    def run(
        self,
        blocks: list[Block],
        doc_id: str,
        source_file: str,
        total_pages: int,
    ) -> SectionTree:
        headings = extract_headings(blocks)
        tree = build_tree(headings, doc_id, source_file, total_pages)

        cache = SummaryCache(cache_dir=self.cache_dir, doc_id=doc_id)
        asyncio.run(generate_summaries(
            tree, blocks, cache,
            ollama_url=self.ollama_url,
            model=self.model,
            max_concurrent=self.max_concurrent,
        ))

        node_count = len(flatten_nodes(tree.root))
        logger.debug(
            "SectionTreePipeline: %d blocks, %d headings → tree with %d nodes",
            len(blocks), len(headings), node_count,
        )
        return tree
