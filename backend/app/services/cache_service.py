from __future__ import annotations

import time
from typing import Any


class CacheService:
    """In-memory cache for recent query results (ArticleBundle + BiasReport).

    Stores results keyed by query string to avoid re-crawling identical queries
    within the TTL window. Replace the in-process dict backend with SQLite or
    Redis for persistence across server restarts.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Any | None:
        """Return cached value for key, or None if missing or expired."""
        # TODO(THE-5): add Redis/SQLite backend for cross-process persistence
        entry = self._store.get(key)
        if entry is not None:
            ts, value = entry
            if time.time() - ts < self.ttl_seconds:
                return value
        return None

    async def set(self, key: str, value: Any) -> None:
        """Store value under key with the current timestamp."""
        # TODO(THE-5): persist to Redis/SQLite instead of in-process dict
        self._store[key] = (time.time(), value)
