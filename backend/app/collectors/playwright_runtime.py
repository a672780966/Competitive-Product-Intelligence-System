"""PlaywrightRuntimeCollector — wraps existing PlaywrightCollector.

Gracefully degrades to DirectHttpCollector if Playwright is not available.
When feature flag COLLECTOR_PLAYWRIGHT_ENABLED is False, returns a blocked
result with failure intelligence instead of silently falling through.
"""
from __future__ import annotations

from typing import Any

from app.collectors.failure_intelligence import FailureAnalysis
from app.collectors.registry import BaseCollectorProvider, CollectResult
from app.core import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PlaywrightRuntimeCollector(BaseCollectorProvider):
    """Wrapper around the existing PlaywrightCollector.

    Uses the existing PlaywrightCollector if Playwright is installed.
    Gracefully degrades to DirectHttpCollector if not available or on error.
    When the feature flag is disabled, returns a blocked CollectResult.
    """

    kind = "playwright"

    def __init__(self) -> None:
        self._playwright_available: bool | None = None
        self._fallback = self._get_fallback()

    @staticmethod
    def _get_fallback() -> BaseCollectorProvider:
        """Lazy-import DirectHttpCollector to avoid circular imports."""
        from app.collectors.direct_http import DirectHttpCollector

        return DirectHttpCollector()

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        """Fetch using Playwright if available, otherwise fallback to direct_http.

        If the COLLECTOR_PLAYWRIGHT_ENABLED feature flag is disabled,
        returns a blocked CollectResult with failure intelligence.
        """
        # Check feature flag first
        settings = get_settings()
        if not settings.COLLECTOR_PLAYWRIGHT_ENABLED:
            logger.warning(
                "playwright_feature_flag_disabled",
                url=url,
            )
            return CollectResult(
                success=False,
                error_code="BLOCKED_SOURCE",
                error_message="Playwright collector is disabled by feature flag COLLECTOR_PLAYWRIGHT_ENABLED=False",
                collector_kind=self.kind,
                failure_intelligence=FailureAnalysis(
                    failure_type="blocked_source",
                    retryable=False,
                    suggested_next="skip_permanent",
                    user_visible_message="Playwright 采集器被功能开关禁用",
                    blocked_reason="Feature flag COLLECTOR_PLAYWRIGHT_ENABLED is disabled",
                ),
            )

        if self._playwright_available is None:
            self._playwright_available = self._check_playwright()

        if not self._playwright_available:
            logger.warning(
                "playwright_not_available_fallback_to_http",
                url=url,
            )
            return await self._fallback.fetch(url, **kwargs)

        try:
            return await self._do_playwright_fetch(url, **kwargs)
        except Exception as exc:
            logger.warning(
                "playwright_fetch_failed_fallback_to_http",
                url=url,
                error=str(exc),
            )
            return await self._fallback.fetch(url, **kwargs)

    def _check_playwright(self) -> bool:
        """Check if playwright is available for import."""
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    async def _do_playwright_fetch(self, url: str, **kwargs: Any) -> CollectResult:
        """Perform fetch using the existing PlaywrightCollector."""
        from app.collectors import get_playwright_collector

        PlaywrightCollector = get_playwright_collector()
        timeout = kwargs.get("timeout", 20)
        collector = PlaywrightCollector()
        result = await collector.fetch(url, timeout=timeout)

        return CollectResult(
            success=result.success,
            final_url=result.final_url,
            http_status=result.http_status,
            page_title=result.page_title,
            raw_html=result.raw_html,
            response_headers=result.response_headers,
            content_hash=result.content_hash,
            error_code=result.error_code.value if result.error_code else None,
            error_message=result.error_message,
            fetch_time_ms=result.fetch_time_ms,
            collector_kind=self.kind,
        )
