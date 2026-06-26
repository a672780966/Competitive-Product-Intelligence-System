"""ScraplingRuntimeCollector — placeholder for scrapling-powered collector.

This is NOT a real provider. It is a stub that raises NotImplementedError
with a clear message indicating the feature is not enabled.
"""
from __future__ import annotations

from typing import Any

from app.collectors.registry import BaseCollectorProvider, CollectResult


class ScraplingRuntimeCollector(BaseCollectorProvider):
    """Placeholder scrapling collector — not enabled by default."""

    kind = "scrapling"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        raise NotImplementedError(
            "Scrapling collector is not enabled. "
            "Set COLLECTOR_SCRAPLING_ENABLED=true and install 'scrapling' package.",
        )
