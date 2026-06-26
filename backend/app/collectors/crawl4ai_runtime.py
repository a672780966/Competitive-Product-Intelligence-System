"""Crawl4AIRuntimeCollector — placeholder for crawl4ai-powered collector.

This is NOT a real provider. It is a stub that raises NotImplementedError
with a clear message indicating the feature is not enabled.
"""
from __future__ import annotations

from typing import Any

from app.collectors.registry import BaseCollectorProvider, CollectResult


class Crawl4AIRuntimeCollector(BaseCollectorProvider):
    """Placeholder crawl4ai collector — not enabled by default."""

    kind = "crawl4ai"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        raise NotImplementedError(
            "Crawl4AI collector is not enabled. "
            "Set COLLECTOR_CRAWL4AI_ENABLED=true and install 'crawl4ai' package.",
        )
