from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

FeatureIndex: TypeAlias = dict[str, list["FeatureRecord"]]


@dataclass
class FeatureRecord:
    feature_type: str          # heading | bullet_item | key_value_pair | repeated_pattern | named_entity
    value: str                 # extracted value
    block_id: str
    doc_id: str
    page_number: int
    key: str | None = None             # key_value_pair: the key part
    entity_subtype: str | None = None  # named_entity: "ip" | "hostname" | "version"
    frequency: int | None = None       # repeated_pattern: count of distinct blocks
