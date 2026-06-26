"""
CPIS V1 — CollectorSelector: strategy pattern for collector selection.

The new CollectorSelector is a pure selector: it decides *which* collector
to use based on source metadata (URL, source_type, risk_level) and
feature flags from the CollectorRuntimeRegistry.

Legacy ``fetch()`` method is retained for backward compatibility with
existing task code in ``app.tasks.collection``.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.collectors.base import CollectResult, FetchErrorCode
from app.collectors.domain_lock import DomainConcurrencyLimiter
from app.collectors.registry import (
    BaseCollectorProvider,
    CollectorRuntimeRegistry,
    get_collector_registry,
)

_MIN_HTML_FOR_USEFUL = 2048  # 2 KB


@dataclass
class SelectResult:
    """Result of a collector selection operation."""

    collector_kind: str
    runtime: BaseCollectorProvider | None
    reason: str


class CollectorSelector:
    """Selects the appropriate collector based on source metadata and feature flags.

    Args:
        max_per_domain: Max concurrent requests per domain (legacy, kept for compat).
        registry: CollectorRuntimeRegistry instance. Uses singleton if not provided.
    """

    def __init__(
        self,
        max_per_domain: int = 2,
        registry: CollectorRuntimeRegistry | None = None,
    ) -> None:
        self._registry = registry or get_collector_registry()
        self._limiter = DomainConcurrencyLimiter(max_per_domain=max_per_domain)

    def select(
        self,
        url: str,
        source_type: str = "other",
        risk_level: str = "low",
    ) -> SelectResult:
        """Select the appropriate collector for a given URL / source metadata.

        Args:
            url: The target URL (used for domain extraction).
            source_type: Source type categorisation (e.g. "product_detail").
            risk_level: Risk level ("low", "medium", "high", "blocked").

        Returns:
            A SelectResult with the chosen collector kind, runtime, and reason.
        """
        # Blocked sources always return the "blocked" kind
        if risk_level == "blocked":
            return SelectResult(
                collector_kind="blocked",
                runtime=None,
                reason="Source risk level is 'blocked' — no collector allowed",
            )

        # direct_http is the only default-enabled collector
        if self._registry.is_enabled("direct_http"):
            return SelectResult(
                collector_kind="direct_http",
                runtime=self._registry.get_provider("direct_http"),
                reason="Default collector: direct_http",
            )

        # Fallback: try other feature-gated collectors (in order)
        for kind in self._registry.get_supported_kinds():
            if kind in ("blocked", "direct_http"):
                continue
            if not self._registry.is_enabled(kind):
                continue
            # Check that this collector kind supports the requested source_type
            meta = self._registry.get_metadata(kind)
            if meta and source_type not in meta.supported_source_types:
                continue
            provider = self._registry.get_provider(kind)
            if provider is not None:
                return SelectResult(
                    collector_kind=kind,
                    runtime=provider,
                    reason=f"Fallback collector: {kind}",
                )

        # Ultimate fallback — no provider available
        return SelectResult(
            collector_kind="direct_http",
            runtime=None,
            reason="No collector available",
        )

    async def fetch(self, url: str, *, timeout: int = 20) -> CollectResult:
        """Legacy: select collector and execute fetch.

        This method wraps ``select()`` + runtime execution for backward
        compatibility with ``app.tasks.collection``. New code should
        use ``select()`` to get the collector, then call ``fetch()``
        on the returned runtime directly.

        Returns:
            A legacy ``base.CollectResult``.
        """
        sel = self.select(url, source_type="other", risk_level="low")

        if sel.collector_kind == "blocked" or sel.runtime is None:
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=sel.reason,
            )

        try:
            reg_result = await sel.runtime.fetch(url, timeout=timeout)

            legacy_code: FetchErrorCode | None = None
            if reg_result.error_code:
                try:
                    legacy_code = FetchErrorCode(reg_result.error_code)
                except ValueError:
                    legacy_code = FetchErrorCode.FETCH_HTTP_ERROR

            return CollectResult(
                success=reg_result.success,
                final_url=reg_result.final_url,
                http_status=reg_result.http_status,
                page_title=reg_result.page_title,
                raw_html=reg_result.raw_html,
                response_headers=reg_result.response_headers,
                content_hash=reg_result.content_hash,
                error_code=legacy_code,
                error_message=reg_result.error_message,
                fetch_time_ms=reg_result.fetch_time_ms,
                used_playwright=(sel.collector_kind == "playwright"),
            )
        except NotImplementedError:
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=f"Collector '{sel.collector_kind}' is not enabled",
            )
        except Exception as exc:
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=str(exc),
            )


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL, defaulting to 'unknown'."""
    try:
        return urlparse(url).hostname or "unknown"
    except Exception:
        return "unknown"


def _should_use_playwright(result: CollectResult) -> bool:
    """Decide whether to fall back to Playwright rendering.

    .. deprecated::
        This function is kept for backward compatibility only.
        The new CollectorSelector does not use it.

    Returns True if:
    - HTTP 403 or 503 (transient / WAF — JS may help)
    - Timeout or connection refused (server may need JS)
    - Empty body or very small (< 2 KB without title)
    """
    if result.success:
        return False  # Already got good content

    # Transient HTTP statuses — try Playwright
    if result.http_status in (403, 429, 503):
        return True

    # Timeout or connection issue — page might need JS
    if result.error_code in (
        FetchErrorCode.FETCH_TIMEOUT,
        FetchErrorCode.CONNECTION_REFUSED,
        FetchErrorCode.DNS_FAILURE,
    ):
        return True

    # Non-transient errors — don't retry
    if result.error_code in (
        FetchErrorCode.CONTENT_TOO_LARGE,
        FetchErrorCode.CAPTCHA_DETECTED,
        FetchErrorCode.LOGIN_REQUIRED,
    ):
        return False

    # HTTP 4xx (not 403/429) — don't retry
    if 400 <= result.http_status < 500 and result.http_status not in (403, 429):
        return False

    # HTTP 5xx (not 503) — don't retry
    if 500 <= result.http_status < 600 and result.http_status != 503:
        return False

    # Empty or very small content — try Playwright
    if result.http_status in (200, 0) and len(result.raw_html) < _MIN_HTML_FOR_USEFUL:
        return True

    return False
