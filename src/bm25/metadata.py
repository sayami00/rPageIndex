from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_INDEX_NAMES = ("page", "section", "feature", "table")


class IndexMetadata:
    """Tracks per-document file hashes and per-index build statistics."""

    def __init__(self, index_root: str):
        self._path = Path(index_root) / "metadata.json"
        self._data: dict = {"indices": {}, "documents": {}}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("metadata.json load failed (%s), starting fresh", exc)
                self._data = {"indices": {}, "documents": {}}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2), encoding="utf-8"
        )

    # ── file hash ─────────────────────────────────────────────────────────────

    @staticmethod
    def file_hash(path: str) -> str:
        """SHA256 of file bytes, first 16 hex chars."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def is_changed(self, doc_id: str, current_hash: str) -> bool:
        stored = self._data["documents"].get(doc_id, {}).get("file_hash")
        return stored != current_hash

    def record_document(self, doc_id: str, source_file: str, file_hash: str) -> None:
        self._data["documents"][doc_id] = {
            "source_file": source_file,
            "file_hash": file_hash,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

    def remove_document(self, doc_id: str) -> None:
        self._data["documents"].pop(doc_id, None)

    def known_doc_ids(self) -> set[str]:
        return set(self._data["documents"].keys())

    # ── index stats ───────────────────────────────────────────────────────────

    def record_index_build(
        self,
        index_name: str,
        document_count: int,
        total_block_count: int = 0,
    ) -> None:
        self._data["indices"][index_name] = {
            "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "document_count": document_count,
            "total_block_count": total_block_count,
        }

    def index_stats(self, index_name: str) -> dict:
        return self._data["indices"].get(index_name, {})

    def all_stats(self) -> dict:
        return dict(self._data)
