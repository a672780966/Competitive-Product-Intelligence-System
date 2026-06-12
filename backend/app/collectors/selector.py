"""
CPIS V1 — CollectorSelector: strategy pattern for fetching.

Flow:
1. Try HttpxCollector first (fast, no overhead).
2. If content is suspicious (login page, captcha, or JS-heavy),
   it still returns the HTML — we just note the heuristic.
3. If HttpxCollector fails with a transient error (timeout, DNS),
   fall back to PlaywrightCollector for JS rendering.
4. If both fail, return the HttpxCollector error.

The decision to fall back to Playwright is based on:
- Empty or very short raw_html (< 2 KB often means JS-required page)
- HTTP 403/503 → try Playwright
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.collectors.base import CollectResult, FetchErrorCode
from app.collectors.domain_lock import DomainConcurrencyLimiter
from app.collectors.httpx_collector import HttpxCollector
from app.collectors.playwright_collector import PlaywrightCollector

_MIN_HTML_FOR_USEFUL = 2048  # 2 KB


class CollectorSelector:
    """Selects and executes the appropriate collector strategy."""

    def __init__(self, max_per_domain: int = 2) -> None:
        self._httpx = HttpxCollector()
        self._playwright = PlaywrightCollector()
        self._limiter = DomainConcurrencyLimiter(max_per_domain=max_per_domain)

    async def fetch(self, url: str, *, timeout: int = 20) -> CollectResult:
        """Fetch a URL, falling back to Playwright if httpx fails.

        Args:
            url: The URL to fetch.
            timeout: Per-request timeout in seconds.

        Returns:
            A normalised CollectResult.
        """
        domain = _extract_domain(url)

        async with self._limiter.limit(domain):
            # Step 1: try httpx
            result = await self._httpx.fetch(url, timeout=timeout)

            # Step 2: check if we should fall back to Playwright
            if _should_use_playwright(result):
                pw_result = await self._playwright.fetch(url, timeout=timeout + 10)
                if pw_result.success:
                    return pw_result

                # Playwright also failed — return original httpx error
                return result

            return result


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL, defaulting to 'unknown'."""
    try:
        return urlparse(url).hostname or "unknown"
    except Exception:
        return "unknown"


def _should_use_playwright(result: CollectResult) -> bool:
    """Decide whether to fall back to Playwright rendering.

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
