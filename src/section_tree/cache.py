from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SummaryCache:
    def __init__(self, cache_dir: str = ".cache/summaries", doc_id: str = ""):
        self._path = Path(cache_dir) / f"{doc_id}_summary_cache.json"
        self._data: dict[str, str] = {}
        self._hits = 0
        self._misses = 0
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Summary cache load failed (%s), starting empty", exc)
                self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @staticmethod
    def _key(title: str, body_snippet: str) -> str:
        return hashlib.sha256(f"{title}|{body_snippet}".encode()).hexdigest()[:16]

    def get(self, title: str, body_snippet: str) -> str | None:
        key = self._key(title, body_snippet)
        result = self._data.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def put(self, title: str, body_snippet: str, summary: str) -> None:
        key = self._key(title, body_snippet)
        self._data[key] = summary
        self._save()

    def stats(self) -> tuple[int, int]:
        """Return (hits, misses)."""
        return self._hits, self._misses
