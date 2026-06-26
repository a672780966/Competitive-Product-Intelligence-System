"""Tests for sitemap discovery."""
from __future__ import annotations

import pytest

from app.collectors.sitemap_discovery import discover_from_sitemap, discover_from_robots


class TestSitemapDiscovery:
    @pytest.mark.asyncio
    async def test_discover_from_sitemaps_org(self):
        """www.sitemaps.org has a sitemap — should find URLs."""
        urls = await discover_from_sitemap("https://www.sitemaps.org", max_urls=5)
        assert len(urls) > 0
        # At least some URLs should be found
        assert all(u.startswith("http") for u in urls)

    @pytest.mark.asyncio
    async def test_no_sitemap_returns_empty(self):
        """httpbin.org has no sitemap — should return empty list."""
        urls = await discover_from_sitemap("https://httpbin.org", max_urls=5)
        assert isinstance(urls, list)
        assert len(urls) == 0

    @pytest.mark.asyncio
    async def test_robots_discovery(self):
        """Check robots.txt discovery (may or may not have sitemap)."""
        sitemap_url = await discover_from_robots("https://books.toscrape.com")
        # books.toscrape.com is a sandbox site, may not have robots.txt
        # The important thing is it doesn't crash and returns str or None
        assert sitemap_url is None or isinstance(sitemap_url, str)

    @pytest.mark.asyncio
    async def test_discover_from_sitemap_max_urls(self):
        """Test that max_urls respects the limit."""
        urls = await discover_from_sitemap(
            "https://www.sitemaps.org", max_urls=3,
        )
        assert len(urls) <= 3
        assert len(urls) > 0  # sitemaps.org has many URLs
        assert len(urls) == 3  # should be exactly 3 due to limit
