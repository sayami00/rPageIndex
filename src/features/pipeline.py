from __future__ import annotations

from src.features.bullet import extract_bullet_items
from src.features.heading import extract_headings
from src.features.key_value import extract_key_value_pairs
from src.features.models import FeatureIndex
from src.features.named_entity import extract_named_entities
from src.features.repeated import extract_repeated_patterns
from src.models.ingestion import Block


class FeaturePipeline:
    """Extract all feature types from a list of cleaned Blocks.

    Each extractor filters REJECT blocks internally and can be used standalone.
    """

    def run(self, blocks: list[Block]) -> FeatureIndex:
        return {
            "heading":          extract_headings(blocks),
            "bullet_item":      extract_bullet_items(blocks),
            "key_value_pair":   extract_key_value_pairs(blocks),
            "repeated_pattern": extract_repeated_patterns(blocks),
            "named_entity":     extract_named_entities(blocks),
        }
