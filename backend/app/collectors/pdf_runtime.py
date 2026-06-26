"""PdfRuntimeCollector — placeholder for PDF document collector.

This is NOT a real provider. It is a stub that raises NotImplementedError
with a clear message indicating the feature is not enabled.
"""
from __future__ import annotations

from typing import Any

from app.collectors.registry import BaseCollectorProvider, CollectResult


class PdfRuntimeCollector(BaseCollectorProvider):
    """Placeholder PDF collector — not enabled by default."""

    kind = "pdf"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        raise NotImplementedError(
            "PDF collector is not enabled. "
            "Set COLLECTOR_PDF_ENABLED=true to enable.",
        )
