from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.models.ingestion import RawBlock

logger = logging.getLogger(__name__)


def derive_doc_id(path: str) -> str:
    return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:16]


def generate_block_id(doc_id: str, page: int, sequence: int) -> str:
    return f"{doc_id}_p{page:04d}_s{sequence:04d}"


class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: str) -> list[RawBlock]:
        ...

    def safe_parse(self, path: str) -> list[RawBlock]:
        try:
            return self.parse(path)
        except Exception as exc:
            logger.error("Parser %s failed on %s: %s", self.__class__.__name__, path, exc)
            return []
