"""RssRuntimeCollector — placeholder for RSS feed collector.

This is NOT a real provider. It is a stub that raises NotImplementedError
with a clear message indicating the feature is not enabled.
"""
from __future__ import annotations

from typing import Any

from app.collectors.registry import BaseCollectorProvider, CollectResult


class RssRuntimeCollector(BaseCollectorProvider):
    """Placeholder RSS collector — not enabled by default."""

    kind = "rss"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        raise NotImplementedError(
            "RSS collector is not enabled. "
            "Set COLLECTOR_RSS_ENABLED=true to enable.",
        )
