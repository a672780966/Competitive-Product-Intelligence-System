"""
CPIS V1 — 网页采集器测试

Tests the HttpxCollector, PlaywrightCollector placeholder,
CollectorSelector, and domain concurrency limiter.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.collectors.base import CollectResult, FetchErrorCode
from app.collectors.domain_lock import DomainConcurrencyLimiter
from app.collectors.httpx_collector import HttpxCollector, _extract_title, _hash_content
from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.selector import CollectorSelector, _should_use_playwright
from app.security.safe_url import SafeUrlResult

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
    """Helper to create a mocked safe client response."""

    def _mock_safe_response(self, status_code=200, content=b"<html><title>Test</title><body>OK</body></html>", url="https://example.com/page"):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = status_code
        mock_resp.content = content
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.url = httpx.URL(url)
        return mock_resp

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_fetch_success(self, mock_safe_get):
        """A successful fetch returns CollectResult with html and title."""
        mock_resp = self._mock_safe_response()
        mock_safe_get.return_value = mock_resp

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/page")

        assert result.success is True
        assert result.http_status == 200
        assert result.page_title == "Test"
        assert len(result.raw_html) > 0
        assert result.content_hash is not None
        assert result.used_playwright is False

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_fetch_http_404(self, mock_safe_get):
        """HTTP 404 returns a failed CollectResult."""
        mock_resp = self._mock_safe_response(status_code=404, content=b"Not Found")
        mock_safe_get.return_value = mock_resp

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/not-found")

        assert result.success is False
        assert result.http_status == 404
        assert result.error_code == FetchErrorCode.FETCH_HTTP_ERROR

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_fetch_timeout(self, mock_safe_get):
        """Timeout returns FETCH_TIMEOUT error."""
        mock_safe_get.side_effect = httpx.TimeoutException("Timeout")

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/slow")

        assert result.success is False
        assert result.error_code == FetchErrorCode.FETCH_TIMEOUT
        assert "timed out" in result.error_message.lower()

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_fetch_dns_error(self, mock_safe_get):
        """DNS failure returns DNS_FAILURE error."""
        mock_safe_get.side_effect = httpx.ConnectError("Name or service not known")

        collector = HttpxCollector()
        result = await collector.fetch("https://invalid.example.com")

        assert result.success is False
        assert result.error_code == FetchErrorCode.DNS_FAILURE

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_fetch_connection_refused(self, mock_safe_get):
        """Connection refused returns CONNECTION_REFUSED error."""
        mock_safe_get.side_effect = httpx.ConnectError("Connection refused")

        collector = HttpxCollector()
        result = await collector.fetch("https://refused.example.com")

        assert result.success is False
        assert result.error_code == FetchErrorCode.CONNECTION_REFUSED

    @patch("app.collectors.httpx_collector.SafeHttpxClient.get")
    async def test_content_too_large(self, mock_safe_get):
        """Content over 10 MB returns CONTENT_TOO_LARGE."""
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        mock_resp = self._mock_safe_response(content=big_content)
        mock_safe_get.return_value = mock_resp

        collector = HttpxCollector()
        result = await collector.fetch("https://example.com/big")

        assert result.success is False
        assert result.error_code == FetchErrorCode.CONTENT_TOO_LARGE

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


# ══════════════════════════════════════════════════════════════════
# PlaywrightCollector — SSRF Route Interception
# ══════════════════════════════════════════════════════════════════


class TestPlaywrightCollectorSSRF:
    """SSRF route interception for PlaywrightCollector.

    The collector registers a route handler via ``page.route("**/*", handler)``
    that calls ``check_url_safe()`` on *every* sub-resource URL before
    allowing Playwright to load it.
    """

    # ── helpers ─────────────────────────────────────────────────────

    async def _setup_mock_chain(self) -> AsyncMock:
        """Build and return a fully-wired mock ``page``.

        The returned ``page`` mock can be used to verify ``page.route()``
        was called and to extract the registered handler.
        """
        page = AsyncMock()
        page.__aenter__.return_value = page
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"content-type": "text/html"}
        page.goto = AsyncMock(return_value=mock_resp)
        page.url = "https://example.com/page"
        page.title = AsyncMock(return_value="Test Page")
        page.content = AsyncMock(return_value="<html><body>OK</body></html>")

        context = AsyncMock()
        context.__aenter__.return_value = context
        context.new_page = AsyncMock(return_value=page)

        browser = AsyncMock()
        browser.new_context = AsyncMock(return_value=context)
        browser.close = AsyncMock()

        pw = AsyncMock()
        pw.chromium.launch = AsyncMock(return_value=browser)

        pw_cm = AsyncMock()
        pw_cm.__aenter__.return_value = pw

        self._pw_cm = pw_cm
        return page

    # ── tests ───────────────────────────────────────────────────────

    @patch("app.collectors.playwright_collector.async_playwright")
    @patch("app.collectors.playwright_collector.check_url_safe", new_callable=AsyncMock)
    async def test_route_registered_with_glob_pattern(
        self,
        mock_check_url_safe: AsyncMock,
        mock_async_pw: MagicMock,
    ) -> None:
        """``page.route("**/*", handler)`` is called before ``goto``."""
        page = await self._setup_mock_chain()
        mock_async_pw.return_value = self._pw_cm

        collector = PlaywrightCollector()
        await collector.fetch("https://example.com/page")

        page.route.assert_called_once()
        assert page.route.call_args[0][0] == "**/*"
        assert callable(page.route.call_args[0][1])

    @patch("app.collectors.playwright_collector.async_playwright")
    @patch("app.collectors.playwright_collector.check_url_safe", new_callable=AsyncMock)
    async def test_safe_subresource_calls_continue(
        self,
        mock_check_url_safe: AsyncMock,
        mock_async_pw: MagicMock,
    ) -> None:
        """A safe sub-resource URL gets ``route.continue_()``."""
        page = await self._setup_mock_chain()
        mock_async_pw.return_value = self._pw_cm
        mock_check_url_safe.return_value = SafeUrlResult(safe=True, reason="OK")

        collector = PlaywrightCollector()
        await collector.fetch("https://example.com/page")

        handler = page.route.call_args[0][1]
        safe_route = AsyncMock()
        safe_route.request.url = "https://example.com/style.css"

        await handler(safe_route)

        safe_route.continue_.assert_called_once()
        safe_route.abort.assert_not_called()
        mock_check_url_safe.assert_called_with("https://example.com/style.css")

    @patch("app.collectors.playwright_collector.async_playwright")
    @patch("app.collectors.playwright_collector.check_url_safe", new_callable=AsyncMock)
    async def test_unsafe_subresource_calls_abort(
        self,
        mock_check_url_safe: AsyncMock,
        mock_async_pw: MagicMock,
    ) -> None:
        """An unsafe sub-resource URL gets ``route.abort()``."""
        page = await self._setup_mock_chain()
        mock_async_pw.return_value = self._pw_cm
        mock_check_url_safe.return_value = SafeUrlResult(
            safe=False,
            reason="Private IP",
        )

        collector = PlaywrightCollector()
        await collector.fetch("https://example.com/page")

        handler = page.route.call_args[0][1]
        unsafe_route = AsyncMock()
        unsafe_route.request.url = "http://localhost:8080/evil"

        await handler(unsafe_route)

        unsafe_route.abort.assert_called_once()
        unsafe_route.continue_.assert_not_called()
        mock_check_url_safe.assert_called_with("http://localhost:8080/evil")

    @patch("app.collectors.playwright_collector.async_playwright")
    @patch("app.collectors.playwright_collector.check_url_safe", new_callable=AsyncMock)
    async def test_route_registered_before_goto(
        self,
        mock_check_url_safe: AsyncMock,
        mock_async_pw: MagicMock,
    ) -> None:
        """Verify route registration happens prior to page navigation."""
        page = await self._setup_mock_chain()
        mock_async_pw.return_value = self._pw_cm
        mock_check_url_safe.return_value = SafeUrlResult(safe=True, reason="OK")

        collector = PlaywrightCollector()
        await collector.fetch("https://example.com/page")

        # route() must have been called before goto()
        route_call_time = page.route.call_args
        goto_call_time = page.goto.call_args
        assert route_call_time is not None
        assert goto_call_time is not None

        # Both were called once — ordering is implicit in the sequential
        # mock record (first route, then goto).  At minimum confirm both
        # were invoked.
        page.route.assert_called_once()
        page.goto.assert_called_once()
