"""Tests for SearchCacheService — TTL-based in-memory cache for search results.

Tests hit, miss, TTL expiry, and basic cache operations.
"""

from __future__ import annotations

import time

import pytest

from app.providers.interfaces import SearchResult
from app.services.search_cache_service import SearchCacheService


class TestSearchCacheService:
    """Tests for the SearchCacheService."""

    def test_cache_miss_on_empty(self):
        """A fresh cache should return None for any query."""
        cache = SearchCacheService()
        result = cache.get("nonexistent query")
        assert result is None

    def test_cache_hit_after_set(self):
        """After setting a value, get should return it."""
        cache = SearchCacheService()
        results = [
            SearchResult(title="Test", url="https://example.com", snippet="Snippet"),
        ]
        cache.set("test query", results)
        cached = cache.get("test query")
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].title == "Test"

    def test_cache_miss_disabled(self):
        """When disabled, get should always return None."""
        cache = SearchCacheService(enabled=False)
        results = [SearchResult(title="Test", url="https://example.com")]
        cache.set("test", results)
        cached = cache.get("test")
        assert cached is None

    def test_cache_set_disabled(self):
        """When disabled, set should not store anything."""
        cache = SearchCacheService(enabled=False)
        results = [SearchResult(title="Test", url="https://example.com")]
        cache.set("test", results)
        assert len(cache._cache) == 0

    def test_ttl_expiry(self):
        """Entries should expire after TTL seconds."""
        cache = SearchCacheService(ttl_seconds=1)
        results = [SearchResult(title="Test", url="https://example.com")]
        cache.set("test", results)

        # Should be immediately available
        assert cache.get("test") is not None

        # Wait for expiry
        time.sleep(1.1)

        # Should now be expired
        assert cache.get("test") is None

    def test_cache_key_is_case_insensitive(self):
        """Cache keys should be case-insensitive (lowercased)."""
        cache = SearchCacheService()
        results = [SearchResult(title="Test", url="https://example.com")]
        cache.set("Xiaomi 14 Ultra", results)
        cached = cache.get("xiaomi 14 ultra")
        assert cached is not None
        assert cached[0].title == "Test"

    def test_cache_with_brand_and_topic(self):
        """Cache should differentiate by brand and topic."""
        cache = SearchCacheService()
        results_a = [SearchResult(title="Result A", url="https://a.com")]
        results_b = [SearchResult(title="Result B", url="https://b.com")]

        cache.set("query", results_a, brand="xiaomi", topic="phone")
        cache.set("query", results_b, brand="samsung", topic="phone")

        cached_a = cache.get("query", brand="xiaomi", topic="phone")
        cached_b = cache.get("query", brand="samsung", topic="phone")

        assert cached_a is not None
        assert cached_a[0].title == "Result A"
        assert cached_b is not None
        assert cached_b[0].title == "Result B"

    def test_invalidate_specific_key(self):
        """Invalidating a specific key should remove only that entry."""
        cache = SearchCacheService()

        cache.set("query1", [SearchResult(title="A", url="https://a.com")])
        cache.set("query2", [SearchResult(title="B", url="https://b.com")])

        cache.invalidate("query1")

        assert cache.get("query1") is None
        assert cache.get("query2") is not None

    def test_invalidate_all(self):
        """Invalidating with no query should clear the entire cache."""
        cache = SearchCacheService()

        cache.set("query1", [SearchResult(title="A", url="https://a.com")])
        cache.set("query2", [SearchResult(title="B", url="https://b.com")])

        cache.invalidate()

        assert cache.get("query1") is None
        assert cache.get("query2") is None

    def test_clear_resets_stats(self):
        """Clear should reset hit/miss counters."""
        cache = SearchCacheService()
        cache.set("query", [SearchResult(title="A", url="https://a.com")])

        # Miss, then hit
        cache.get("other_query")
        cached = cache.get("query")
        assert cached is not None

        stats_before = cache.stats
        assert stats_before["hits"] == 1
        assert stats_before["misses"] == 1

        cache.clear()

        stats_after = cache.stats
        assert stats_after["hits"] == 0
        assert stats_after["misses"] == 0
        assert stats_after["size"] == 0

    def test_stats(self):
        """Stats should track hits, misses, size, and TTL."""
        cache = SearchCacheService(ttl_seconds=300)

        # Misses
        cache.get("q1")
        cache.get("q2")

        # Set and hit
        cache.set("q1", [SearchResult(title="A", url="https://a.com")])
        cache.get("q1")
        cache.get("q1")

        stats = cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["size"] == 1
        assert stats["ttl_seconds"] == 300

    def test_enabled_property(self):
        """The enabled property should reflect constructor input."""
        assert SearchCacheService(enabled=True).enabled is True
        assert SearchCacheService(enabled=False).enabled is False
        # Default should be True (from config or constructor default)
        assert SearchCacheService().enabled is True
