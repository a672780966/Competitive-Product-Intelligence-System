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
from app.core.logging import get_logger
from app.security.safe_url import check_url_safe

logger = get_logger(__name__)

_MAX_HTML_BYTES = 10 * 1024 * 1024  # 10 MB


class PlaywrightCollector(BaseCollector):
    """Fetch a page using Playwright (headless Chromium, JS rendered)."""

    _browser_lock = asyncio.Lock()
    _browser_context = None  # Shared browser instance

    async def fetch(self, url: str, *, timeout: int = 30) -> CollectResult:
        """Fetch URL with Playwright, return normalised result.

        Uses proper async context managers for resource management.
        """
        settings = get_settings()
        user_agent = settings.COLLECTION_USER_AGENT
        start = time.monotonic()

        try:
            result = await self._fetch_with_playwright(url, user_agent, timeout)
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(
                "playwright_fetch_error",
                url=url,
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=elapsed,
            )
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
        """Internal Playwright fetch with proper resource management.

        ✅ 使用 async with 管理 context 和 page 生命周期，避免资源泄漏。
        """
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
            try:
                # ✅ async with 确保 context 自动关闭
                async with await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1280, "height": 800},
                    ignore_https_errors=False,
                    java_script_enabled=True,
                ) as context:
                    # ✅ async with 确保 page 自动关闭
                    async with await context.new_page() as page:
                        # ── SSRF protection: intercept all sub-resources ──
                        async def _intercept_request(route):
                            url = route.request.url
                            result = await check_url_safe(url)
                            if result.safe:
                                await route.continue_()
                            else:
                                logger.warning(
                                    "playwright_ssrf_blocked",
                                    url=url,
                                )
                                await route.abort()

                        await page.route("**/*", _intercept_request)

                        try:
                            response = await page.goto(
                                url,
                                wait_until="domcontentloaded",
                                timeout=timeout * 1000,
                            )

                            if response is None:
                                logger.warning(
                                    "playwright_empty_response",
                                    url=url,
                                )
                                return CollectResult(
                                    success=False,
                                    error_code=FetchErrorCode.EMPTY_RESPONSE,
                                    error_message="No response from page.goto()",
                                )

                            status = response.status
                            final_url = page.url
                            page_title = await page.title() or ""

                            html_content = await page.content()
                            content = html_content.encode("utf-8")

                            if len(content) > _MAX_HTML_BYTES:
                                logger.warning(
                                    "playwright_content_too_large",
                                    url=url,
                                    size_bytes=len(content),
                                )
                                return CollectResult(
                                    success=False,
                                    final_url=final_url,
                                    http_status=status,
                                    error_code=FetchErrorCode.CONTENT_TOO_LARGE,
                                    error_message=f"Content exceeds 10 MB ({len(content)} bytes)",
                                )

                            headers = dict(response.headers) if response.headers else {}
                            content_hash = hashlib.sha256(content).hexdigest()

                            logger.debug(
                                "playwright_fetch_success",
                                url=url,
                                status=status,
                                content_size=len(content),
                            )

                            return CollectResult(
                                success=True,
                                final_url=final_url,
                                http_status=status,
                                page_title=page_title,
                                raw_html=content,
                                response_headers=headers,
                                content_hash=content_hash,
                            )

                        except TimeoutError:
                            logger.warning(
                                "playwright_timeout",
                                url=url,
                                timeout_ms=timeout * 1000,
                            )
                            return CollectResult(
                                success=False,
                                error_code=FetchErrorCode.FETCH_TIMEOUT,
                                error_message=f"Playwright timeout after {timeout}s",
                            )
                        except Exception as page_exc:
                            logger.error(
                                "playwright_page_error",
                                url=url,
                                error=str(page_exc),
                                error_type=type(page_exc).__name__,
                            )
                            raise  # Re-raise 以便上层 catch
                        # ✅ page 自动通过 async with 关闭
                    # ✅ context 自动通过 async with 关闭
            except Exception as exc:
                error_str = str(exc)
                logger.error(
                    "playwright_context_error",
                    url=url,
                    error=error_str,
                    error_type=type(exc).__name__,
                )
                return CollectResult(
                    success=False,
                    error_code=FetchErrorCode.PLAYWRIGHT_ERROR,
                    error_message=error_str,
                )
            finally:
                # ✅ 确保 browser 总是被关闭
                try:
                    await browser.close()
                    logger.debug("playwright_browser_closed")
                except Exception as close_exc:
                    logger.warning(
                        "playwright_browser_close_error",
                        error=str(close_exc),
                    )
