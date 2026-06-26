"""DirectHttpCollector — uses httpx to fetch URL content.

This is the primary, always-available collector in the runtime registry.
Wraps httpx to return raw HTML + metadata.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from app.collectors.registry import BaseCollectorProvider, CollectResult
from app.core import get_settings

_MAX_HTML_BYTES = 10 * 1024 * 1024  # 10 MB


def _extract_title(html: bytes) -> str:
    """Extract the page <title> from raw HTML bytes."""
    try:
        text = html.decode("utf-8", errors="replace")
        start = text.lower().find("<title")
        if start == -1:
            return ""
        end_tag = text.find(">", start)
        if end_tag == -1:
            return ""
        end_title = text.find("</title>", end_tag)
        if end_title == -1:
            return ""
        return text[end_tag + 1 : end_title].strip()[:512]
    except Exception:
        return ""


def _hash_content(content: bytes) -> str:
    """Return SHA-256 hex digest of content."""
    return hashlib.sha256(content).hexdigest()


class DirectHttpCollector(BaseCollectorProvider):
    """Collector that uses httpx to fetch URL content directly.

    This is the primary, always-available collector.
    Returns raw HTML + metadata in a CollectResult.
    """

    kind = "direct_http"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        """Fetch URL with httpx, return normalised result."""
        settings = get_settings()
        user_agent = settings.COLLECTION_USER_AGENT
        timeout = kwargs.get("timeout", 20)
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                follow_redirects=True,
                max_redirects=5,
                headers={"User-Agent": user_agent},
            ) as client:
                response = await client.get(url)
        except httpx.TimeoutException:
            elapsed = int((time.monotonic() - start) * 1000)
            return CollectResult(
                success=False,
                error_code="FETCH_TIMEOUT",
                error_message=f"Request timed out after {timeout}s",
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
            )
        except httpx.ConnectError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            error_str = str(exc).lower()
            error_code = "CONNECTION_REFUSED"
            if "name" in error_str or "resolve" in error_str or "nodename" in error_str:
                error_code = "DNS_FAILURE"
            return CollectResult(
                success=False,
                error_code=error_code,
                error_message=f"Connection error: {exc}",
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
            )
        except httpx.RequestError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return CollectResult(
                success=False,
                error_code="FETCH_HTTP_ERROR",
                error_message=str(exc),
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
            )

        elapsed = int((time.monotonic() - start) * 1000)

        # Check HTTP status
        if response.status_code >= 400:
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code="FETCH_HTTP_ERROR",
                error_message=f"HTTP {response.status_code}",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
            )

        # Check content size
        content = response.content
        if len(content) > _MAX_HTML_BYTES:
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code="CONTENT_TOO_LARGE",
                error_message=f"Content exceeds 10 MB ({len(content)} bytes)",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
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
            collector_kind=self.kind,
        )
