from __future__ import annotations

import os

from src.models.index import PageRecord
from src.models.query import Evidence

SYSTEM_PROMPT = """\
You are a document assistant. Answer using ONLY the provided context pages.
Do not use any knowledge outside the context.
If the answer is not in the context, say: "This information is not in the provided documents."

Always end your response with a CITATIONS block in exactly this format:
CITATIONS:
- [file: {filename}, page: {page_number}]"""

_TYPE_INSTRUCTIONS: dict[str, str] = {
    "page_lookup":    "Answer in prose. Cite the page(s) where you found this information.",
    "section_lookup": "Identify the section name and page range. Answer in prose with section and page citations.",
    "table_query":    "Give the exact value from the table. Cite the table's file and page number.",
    "find_all":       "List every occurrence as a numbered list. Include the page number for each item.",
}


def format_context_page(page: PageRecord) -> str:
    section = page.section_path or "no section"
    filename = os.path.basename(page.source_file)
    parts = [f"--- Page {page.page_number} ({section}) | {filename} ---"]
    if page.heading_text.strip():
        parts.append(page.heading_text.strip())
    if page.body_text.strip():
        parts.append(page.body_text.strip())
    if page.table_text.strip():
        parts.append(page.table_text.strip())
    if page.truncated:
        parts.append("[TRUNCATED]")
    return "\n".join(parts)


def build_answer_prompt(query: str, query_type: str, evidence: Evidence) -> str:
    context_blocks = "\n\n".join(format_context_page(p) for p in evidence.pages)
    instruction = _TYPE_INSTRUCTIONS.get(query_type, _TYPE_INSTRUCTIONS["page_lookup"])
    return (
        f"SYSTEM:\n{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context_blocks}\n\n"
        f"QUESTION:\n{query}\n\n"
        f"{instruction}"
    )
