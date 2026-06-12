"""
CPIS V1 — 网页采集器测试

Tests the HttpxCollector, PlaywrightCollector placeholder,
CollectorSelector, and domain concurrency limiter.
"""

from __future__ import annotations

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.collectors.base import CollectResult, FetchErrorCode
from app.collectors.domain_lock import DomainConcurrencyLimiter
from app.collectors.httpx_collector import HttpxCollector, _extract_title, _hash_content
from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.selector import CollectorSelector, _should_use_playwright


# ══════════════════════════════════════════════════════════════════
# Domain Concurrency Limiter
# ══════════════════════════════════════════════════════════════════


class TestDomainConcurrencyLimiter:
    def test_same_domain_shares_semaphore(self):
        limiter = DomainConcurrencyLimiter(max_per_domain=2)
        sem1 = limiter.limit("example.com")
        sem2 = limiter.limit("example.com")
        assert sem1 is sem2

    def test_different_domains_have_different_semaphores(self):
        limiter = DomainConcurrencyLimiter(max_per_domain=2)
        sem1 = limiter.limit("example.com")
        sem2 = limiter.limit("other.com")
        assert sem1 is not sem2

    def test_release_all_clears_state(self):
        limiter = DomainConcurrencyLimiter(max_per_domain=2)
        limiter.limit("example.com")
        limiter.release_all()
        # After release, should get a new semaphore
        assert len(limiter._semaphores) == 0


# ══════════════════════════════════════════════════════════════════
# Title extraction
# ══════════════════════════════════════════════════════════════════


class TestTitleExtraction:
    def test_extract_title_normal(self):
        html = b"<html><head><title>My Product - Official Site</title></head><body><p>Hello</p></body></html>"
        title = _extract_title(html)
        assert title == "My Product - Official Site"

    def test_extract_title_no_title(self):
        html = b"<html><body><p>No title here</p></body></html>"
        title = _extract_title(html)
        assert title == ""

    def test_extract_title_empty_title(self):
        html = b"<html><head><title></title></head><body></body></html>"
        title = _extract_title(html)
        assert title == ""


class TestHashContent:
    def test_hash_is_deterministic(self):
        h1 = _hash_content(b"hello world")
        h2 = _hash_content(b"hello world")
        assert h1 == h2

    def test_hash_differs_for_different_content(self):
        h1 = _hash_content(b"hello world")
        h2 = _hash_content(b"hello world!")
        assert h1 != h2


# ══════════════════════════════════════════════════════════════════
# HttpxCollector
# ══════════════════════════════════════════════════════════════════


class TestHttpxCollector:
    """Helper to create a mocked httpx client response."""

    def _mock_response(self, status_code=200, content=b"<html><title>Test</title><body>OK</body></html>", url="https://example.com/page"):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = status_code
        mock_resp.content = content
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.url = httpx.URL(url)
        return mock_resp

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_fetch_success(self, mock_client_cls):
        """A successful fetch returns CollectResult with html and title."""
        mock_resp = self._mock_response()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/page")

        assert result.success is True
        assert result.http_status == 200
        assert result.page_title == "Test"
        assert len(result.raw_html) > 0
        assert result.content_hash is not None
        assert result.used_playwright is False

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_fetch_http_404(self, mock_client_cls):
        """HTTP 404 returns a failed CollectResult."""
        mock_resp = self._mock_response(status_code=404, content=b"Not Found")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/not-found")

        assert result.success is False
        assert result.http_status == 404
        assert result.error_code == FetchErrorCode.FETCH_HTTP_ERROR

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_fetch_timeout(self, mock_client_cls):
        """Timeout returns FETCH_TIMEOUT error."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/slow")

        assert result.success is False
        assert result.error_code == FetchErrorCode.FETCH_TIMEOUT
        assert "timed out" in result.error_message.lower()

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_fetch_dns_error(self, mock_client_cls):
        """DNS failure returns DNS_FAILURE error (raises as ConnectError in httpx 0.28+)."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Name or service not known"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://invalid.example.com")

        assert result.success is False
        assert result.error_code == FetchErrorCode.DNS_FAILURE

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_fetch_connection_refused(self, mock_client_cls):
        """Connection refused returns CONNECTION_REFUSED error."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://refused.example.com")

        assert result.success is False
        assert result.error_code == FetchErrorCode.CONNECTION_REFUSED

    @patch("app.collectors.httpx_collector.httpx.AsyncClient")
    async def test_content_too_large(self, mock_client_cls):
        """Content over 10 MB returns CONTENT_TOO_LARGE."""
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        mock_resp = self._mock_response(content=big_content)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/big")

        assert result.success is False
        assert result.error_code == FetchErrorCode.CONTENT_TOO_LARGE

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/big")

        assert result.success is False
        assert result.error_code == FetchErrorCode.CONTENT_TOO_LARGE


# ══════════════════════════════════════════════════════════════════
# CollectorSelector — fallback logic
# ══════════════════════════════════════════════════════════════════


class TestShouldUsePlaywright:
    def test_success_returns_false(self):
        result = CollectResult(success=True, raw_html=b"<html><body>OK</body></html>")
        assert _should_use_playwright(result) is False

    def test_http_403_triggers_fallback(self):
        result = CollectResult(success=False, http_status=403)
        assert _should_use_playwright(result) is True

    def test_http_429_triggers_fallback(self):
        result = CollectResult(success=False, http_status=429)
        assert _should_use_playwright(result) is True

    def test_http_503_triggers_fallback(self):
        result = CollectResult(success=False, http_status=503)
        assert _should_use_playwright(result) is True

    def test_http_404_does_not_trigger(self):
        result = CollectResult(success=False, http_status=404)
        assert _should_use_playwright(result) is False

    def test_http_500_does_not_trigger(self):
        result = CollectResult(success=False, http_status=500)
        assert _should_use_playwright(result) is False

    def test_empty_body_with_200_triggers_fallback(self):
        result = CollectResult(success=False, http_status=200, raw_html=b"<html></html>")
        assert _should_use_playwright(result) is True

    def test_timeout_triggers_fallback(self):
        result = CollectResult(
            success=False, error_code=FetchErrorCode.FETCH_TIMEOUT,
        )
        assert _should_use_playwright(result) is True

    def test_content_too_large_does_not_trigger(self):
        result = CollectResult(
            success=False, error_code=FetchErrorCode.CONTENT_TOO_LARGE,
        )
        assert _should_use_playwright(result) is False


class TestCollectorSelector:
    @patch.object(HttpxCollector, "fetch")
    async def test_httpx_success_returns_directly(self, mock_httpx_fetch):
        """When httpx succeeds, no Playwright fallback is attempted."""
        mock_httpx_fetch.return_value = CollectResult(
            success=True, raw_html=b"<html><body>OK</body></html>",
        )
        selector = CollectorSelector(max_per_domain=5)
        result = await selector.fetch("https://example.com/page")
        assert result.success is True

    @patch.object(HttpxCollector, "fetch")
    @patch.object(PlaywrightCollector, "fetch")
    async def test_httpx_403_falls_back_to_playwright(self, mock_pw_fetch, mock_httpx_fetch):
        """HTTP 403 from httpx triggers Playwright fallback."""
        mock_httpx_fetch.return_value = CollectResult(
            success=False, http_status=403, raw_html=b"",
        )
        mock_pw_fetch.return_value = CollectResult(
            success=True, raw_html=b"<html><body>Rendered OK</body></html>",
            used_playwright=True,
        )
        selector = CollectorSelector(max_per_domain=5)
        result = await selector.fetch("https://example.com/page")
        assert result.success is True
        assert result.used_playwright is True

    @patch.object(HttpxCollector, "fetch")
    @patch.object(PlaywrightCollector, "fetch")
    async def test_both_collectors_fail_returns_httpx_error(self, mock_pw_fetch, mock_httpx_fetch):
        """When both collectors fail, return the httpx error."""
        mock_httpx_fetch.return_value = CollectResult(
            success=False, http_status=403, error_message="Forbidden",
        )
        mock_pw_fetch.return_value = CollectResult(
            success=False, error_code=FetchErrorCode.PLAYWRIGHT_ERROR,
            error_message="Browser crash",
        )
        selector = CollectorSelector(max_per_domain=5)
        result = await selector.fetch("https://example.com/page")
        assert result.success is False
        assert result.error_message == "Forbidden"  # httpx error, not playwright
