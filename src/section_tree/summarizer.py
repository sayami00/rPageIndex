from __future__ import annotations

import asyncio
import logging
import time

import aiohttp

from src.models.ingestion import Block
from src.section_tree.cache import SummaryCache
from src.section_tree.models import SectionTree, TreeNode

logger = logging.getLogger("section_tree.summarizer")

_MAX_INPUT_TOKENS = 500
_PROMPT_OVERHEAD_TOKENS = 15   # "Summarize this section in one sentence: " + " — "
_INDEXABLE_GATES = frozenset({"PASS", "FLAG"})


def _body_snippet(node: TreeNode, blocks: list[Block]) -> str:
    """First 200 chars of first paragraph block within node's page span."""
    first, last = node.page_spans
    for b in sorted(blocks, key=lambda x: (x.page_number, x.sequence)):
        if (
            first <= b.page_number <= last
            and b.block_type == "paragraph"
            and b.gate_status in _INDEXABLE_GATES
        ):
            return b.clean_text[:200]
    return ""


def _truncate_to_budget(title: str, body: str) -> str:
    budget_chars = (_MAX_INPUT_TOKENS - _PROMPT_OVERHEAD_TOKENS) * 4
    available = budget_chars - len(title) - 3  # " — "
    if available <= 0:
        return ""
    return body[:available]


def flatten_nodes(root: TreeNode) -> list[TreeNode]:
    """Pre-order DFS, skipping root sentinel."""
    result: list[TreeNode] = []

    def _dfs(node: TreeNode) -> None:
        if node.depth > 0:
            result.append(node)
        for child in node.children:
            _dfs(child)

    _dfs(root)
    return result


async def _summarize_one(
    node: TreeNode,
    body_snippet: str,
    cache: SummaryCache,
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    ollama_url: str,
    model: str,
) -> None:
    cached = cache.get(node.title, body_snippet)
    if cached is not None:
        node.summary = cached
        return

    snippet = _truncate_to_budget(node.title, body_snippet)
    prompt = f"Summarize this section in one sentence: {node.title}"
    if snippet:
        prompt += f" — {snippet}"

    input_tokens_est = len(prompt) // 4
    t0 = time.monotonic()

    async with sem:
        try:
            payload = {"model": model, "prompt": prompt, "stream": False}
            async with session.post(
                f"{ollama_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json(content_type=None)
                summary = data.get("response", "").strip()
                elapsed = time.monotonic() - t0
                logger.info(
                    "[ollama] node=%s input_tokens≈%d response_time=%.2fs status=ok",
                    node.node_id, input_tokens_est, elapsed,
                )
                node.summary = summary
                cache.put(node.title, body_snippet, summary)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error(
                "[ollama] node=%s input_tokens≈%d response_time=%.2fs status=error: %s",
                node.node_id, input_tokens_est, elapsed, exc,
            )
            # Leave summary="" — non-fatal, tree still returned


async def generate_summaries(
    tree: SectionTree,
    blocks: list[Block],
    cache: SummaryCache,
    ollama_url: str,
    model: str,
    max_concurrent: int,
) -> None:
    nodes = flatten_nodes(tree.root)
    if not nodes:
        return

    sem = asyncio.Semaphore(max_concurrent)
    snippets = [_body_snippet(node, blocks) for node in nodes]

    async with aiohttp.ClientSession() as session:
        tasks = [
            _summarize_one(node, snippet, cache, sem, session, ollama_url, model)
            for node, snippet in zip(nodes, snippets)
        ]
        await asyncio.gather(*tasks)

    hits, misses = cache.stats()
    total = hits + misses
    pct = int(100 * hits / total) if total else 0
    logger.info(
        "[section_tree] summary cache: %d hits / %d nodes (%d%% cached)",
        hits, total, pct,
    )
