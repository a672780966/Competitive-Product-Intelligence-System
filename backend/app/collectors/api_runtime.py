"""ApiRuntimeCollector — placeholder for API-based data collector.

This is NOT a real provider. It is a stub that raises NotImplementedError
with a clear message indicating the feature is not enabled.
"""
from __future__ import annotations

from typing import Any

from app.collectors.registry import BaseCollectorProvider, CollectResult


class ApiRuntimeCollector(BaseCollectorProvider):
    """Placeholder API collector — not enabled by default."""

    kind = "api"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        raise NotImplementedError(
            "API collector is not enabled. "
            "Set COLLECTOR_API_ENABLED=true to enable.",
        )
