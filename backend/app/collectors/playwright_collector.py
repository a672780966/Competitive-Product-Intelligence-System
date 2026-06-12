"""
CPIS V1 — PlaywrightCollector: JS-rendered page fetcher.

Used when httpx returns insufficient content for useful extraction.
Leverages Playwright to render JavaScript-heavy pages.
"""

from __future__ import annotations

import asyncio
import hashlib
import time

from playwright.async_api import async_playwright

from app.collectors.base import BaseCollector, CollectResult, FetchErrorCode
from app.core import get_settings

_MAX_HTML_BYTES = 10 * 1024 * 1024  # 10 MB


class PlaywrightCollector(BaseCollector):
    """Fetch a page using Playwright (headless Chromium, JS rendered)."""

    _browser_lock = asyncio.Lock()
    _browser_context = None  # Shared browser instance

    async def fetch(self, url: str, *, timeout: int = 30) -> CollectResult:
        """Fetch URL with Playwright, return normalised result.

        Uses a shared browser instance for efficiency.
        """
        settings = get_settings()
        user_agent = settings.COLLECTION_USER_AGENT
        start = time.monotonic()

        try:
            result = await self._fetch_with_playwright(url, user_agent, timeout)
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.PLAYWRIGHT_ERROR,
                error_message=f"Playwright error: {exc}",
                fetch_time_ms=elapsed,
                used_playwright=True,
            )

        elapsed = int((time.monotonic() - start) * 1000)
        result.fetch_time_ms = elapsed
        result.used_playwright = True
        return result

    async def _fetch_with_playwright(
        self,
        url: str,
        user_agent: str,
        timeout: int,
    ) -> CollectResult:
        """Internal Playwright fetch with shared browser."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=False,
                java_script_enabled=True,
            )
            page = await context.new_page()

            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

                if response is None:
                    await browser.close()
                    return CollectResult(
                        success=False,
                        error_code=FetchErrorCode.EMPTY_RESPONSE,
                        error_message="No response from page.goto()",
                    )

                status = response.status
                final_url = page.url
                page_title = await page.title() or ""

                # Get the full HTML after JS rendering
                html_content = await page.content()
                content = html_content.encode("utf-8")

                if len(content) > _MAX_HTML_BYTES:
                    await browser.close()
                    return CollectResult(
                        success=False,
                        final_url=final_url,
                        http_status=status,
                        error_code=FetchErrorCode.CONTENT_TOO_LARGE,
                        error_message=f"Content exceeds 10 MB ({len(content)} bytes)",
                    )

                headers = dict(response.headers) if response.headers else {}
                content_hash = hashlib.sha256(content).hexdigest()

                await browser.close()
                return CollectResult(
                    success=True,
                    final_url=final_url,
                    http_status=status,
                    page_title=page_title,
                    raw_html=content,
                    response_headers=headers,
                    content_hash=content_hash,
                )

            except Exception as exc:
                await browser.close()
                error_str = str(exc)
                if "Timeout" in error_str:
                    return CollectResult(
                        success=False,
                        error_code=FetchErrorCode.FETCH_TIMEOUT,
                        error_message=error_str,
                    )
                return CollectResult(
                    success=False,
                    error_code=FetchErrorCode.PLAYWRIGHT_ERROR,
                    error_message=error_str,
                )
