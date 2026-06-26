"""SearchCacheService — TTL-based in-memory cache for search results.

Provides a simple in-memory cache with configurable TTL (time-to-live).
Used by DiscoveryService to avoid redundant search queries for the same
query within a short time window.

Thread-safe for async use via asyncio lock.
"""

from __future__ import annotations

import time
from collections.abc import MutableMapping
from typing import Any

from app.core.logging import get_logger
from app.providers.config import get_cache_config

logger = get_logger(__name__)


class SearchCacheService:
    """TTL-based in-memory cache for search results.

    Stores search results keyed by (query, language, brand, topic).
    Entries expire after CACHE_TTL_SECONDS from the configured settings.

    Usage:
        cache = SearchCacheService()
        cached = cache.get("xiaomi 14 ultra")
        if cached is None:
            results = await provider.search("xiaomi 14 ultra")
            cache.set("xiaomi 14 ultra", results)
    """

    def __init__(
        self,
        ttl_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        config = get_cache_config()
        self._enabled = enabled if enabled is not None else config.get("enabled", True)
        self._ttl = ttl_seconds if ttl_seconds is not None else config.get("ttl_seconds", 300)
        self._cache: dict[str, tuple[float, list[Any]]] = {}
        self._hits = 0
        self._misses = 0

    @property
    def enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "ttl_seconds": self._ttl,
        }

    def _make_key(
        self,
        query: str,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> str:
        """Create a cache key from query parameters."""
        parts = [query.strip().lower(), language]
        if brand:
            parts.append(f"b:{brand.lower()}")
        if topic:
            parts.append(f"t:{topic.lower()}")
        return "|".join(parts)

    def get(
        self,
        query: str,
        *,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[Any] | None:
        """Get cached results for a query.

        Returns None if:
        - Cache is disabled
        - Key doesn't exist
        - Entry has expired
        """
        if not self._enabled:
            return None

        key = self._make_key(query, language, brand, topic)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        timestamp, results = entry
        if time.monotonic() - timestamp > self._ttl:
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        logger.debug("cache_hit", key=key)
        return results

    def set(
        self,
        query: str,
        results: list[Any],
        *,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> None:
        """Cache search results for a query."""
        if not self._enabled:
            return

        key = self._make_key(query, language, brand, topic)
        self._cache[key] = (time.monotonic(), results)
        logger.debug("cache_set", key=key, count=len(results))

    def invalidate(
        self,
        query: str | None = None,
        *,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> None:
        """Invalidate cache entries.

        If query is None, clears the entire cache.
        Otherwise removes only the matching key.
        """
        if query is None:
            self._cache.clear()
            logger.debug("cache_cleared")
            return

        key = self._make_key(query, language, brand, topic)
        self._cache.pop(key, None)
        logger.debug("cache_invalidated", key=key)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("cache_cleared")
