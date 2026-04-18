from __future__ import annotations

from src.tables.models import TableOutput
from src.tables.serializer import serialize_table


def build_table_outputs(groups: list[list[dict]]) -> list[TableOutput]:
    """Convert grouped table_data into merged TableOutput objects.

    Each group becomes one logical table. Rows from all pages are merged.
    """
    outputs: list[TableOutput] = []

    for group in groups:
        first_block = group[0]["block"]
        table_id = first_block.block_id
        group_id = table_id

        # Merge rows from all pages in the group
        headers = group[0]["headers"]
        all_structured: list[dict] = []
        source_pages: list[int] = []

        for item in group:
            source_pages.append(item["block"].page_number)
            all_structured.extend(item["structured"])

        search_rows = serialize_table(headers, all_structured)

        outputs.append(TableOutput(
            table_id=table_id,
            doc_id=first_block.doc_id,
            source_pages=source_pages,
            headers=headers,
            structured=all_structured,
            search_rows=search_rows,
            continuation_of=None,
            continuation_group_id=group_id,
        ))

    return outputs
