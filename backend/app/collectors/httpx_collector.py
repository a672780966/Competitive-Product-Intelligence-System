"""
CPIS V1 — HttpxCollector: static HTML fetcher.

Fetches pages using httpx (no JS rendering).
Uses ``SafeHttpxClient`` for SSRF protection.
"""

from __future__ import annotations

import hashlib
import time
from html.parser import HTMLParser

import httpx

from app.collectors.base import BaseCollector, CollectResult, FetchErrorCode
from app.core import get_settings
from app.security.safe_http_client import SafeHttpxClient

_MAX_HTML_BYTES = 10 * 1024 * 1024  # 10 MB


class _TitleParser(HTMLParser):
    """Minimal HTML parser to extract <title> content."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _extract_title(html: bytes) -> str:
    """Extract the page <title> from raw HTML bytes."""
    try:
        parser = _TitleParser()
        parser.feed(html.decode("utf-8", errors="replace"))
        return parser.title.strip()[:512]
    except Exception:
        return ""


def _hash_content(content: bytes) -> str:
    """Return SHA-256 hex digest of content."""
    return hashlib.sha256(content).hexdigest()


class HttpxCollector(BaseCollector):
    """Fetch a page using httpx (static HTML, no JS).

    Uses :class:`SafeHttpxClient` to enforce SSRF protection
    on every request and each redirect hop.
    """

    async def fetch(self, url: str, *, timeout: int = 20) -> CollectResult:
        """Fetch URL with safe httpx client, return normalised result.

        The :class:`SafeHttpxClient` handles:
        - SSRF checks before the request and on every redirect
        - Content-Type allowlisting
        - Response body size limiting
        - Manual redirect following (max 5 hops)
        """
        settings = get_settings()
        user_agent = settings.COLLECTION_USER_AGENT
        start = time.monotonic()

        safe_client = SafeHttpxClient(
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

        try:
            response = await safe_client.get(url)
        except ValueError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            error_str = str(exc)
            # SSRF / safety violations
            if "blocked" in error_str or "metadata" in error_str or "private" in error_str:
                return CollectResult(
                    success=False,
                    error_code=FetchErrorCode.CONNECTION_REFUSED,
                    error_message=error_str,
                    fetch_time_ms=elapsed,
                    used_playwright=False,
                )
            # Content type / size violations
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=error_str,
                fetch_time_ms=elapsed,
                used_playwright=False,
            )
        except httpx.TimeoutException:
            elapsed = int((time.monotonic() - start) * 1000)
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_TIMEOUT,
                error_message=f"Request timed out after {timeout}s",
                fetch_time_ms=elapsed,
                used_playwright=False,
            )
        except httpx.ConnectError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            error_str = str(exc)
            error_code = FetchErrorCode.CONNECTION_REFUSED
            # DNS errors surface as ConnectError in httpx 0.28+
            if "name" in error_str.lower() or "resolve" in error_str.lower() or "nodename" in error_str.lower():
                error_code = FetchErrorCode.DNS_FAILURE
            return CollectResult(
                success=False,
                error_code=error_code,
                error_message=f"Connection error: {exc}",
                fetch_time_ms=elapsed,
                used_playwright=False,
            )
        except httpx.RequestError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return CollectResult(
                success=False,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=str(exc),
                fetch_time_ms=elapsed,
                used_playwright=False,
            )

        elapsed = int((time.monotonic() - start) * 1000)

        # Check HTTP status
        if response.status_code >= 400:
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code=FetchErrorCode.FETCH_HTTP_ERROR,
                error_message=f"HTTP {response.status_code}",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                used_playwright=False,
            )

        # Check content size (belt-and-suspenders with SafeHttpxClient's limit)
        content = response.content
        if len(content) > _MAX_HTML_BYTES:
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code=FetchErrorCode.CONTENT_TOO_LARGE,
                error_message=f"Content exceeds 10 MB ({len(content)} bytes)",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                used_playwright=False,
            )

        page_title = _extract_title(content)
        content_hash = _hash_content(content)

        return CollectResult(
            success=True,
            final_url=str(response.url),
            http_status=response.status_code,
            page_title=page_title,
            raw_html=content,
            response_headers=dict(response.headers),
            content_hash=content_hash,
            fetch_time_ms=elapsed,
            used_playwright=False,
        )
