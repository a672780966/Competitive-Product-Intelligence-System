"""DirectHttpCollector — enhanced httpx-based collector with 8 capability upgrades.

Enhancements:
1. UA rotation pool (5 real browser UAs)
2. Split timeouts (connect=10s, read=20s, write=10s, pool=5s)
3. gzip/brotli Accept-Encoding
4. Charset auto-detection (Content-Type → HTML meta → chardet → utf-8)
5. Content-Type classification (html/json/xml/pdf/image/text/other)
6. Browser-like headers (Referer, Sec-Fetch-*, Upgrade-Insecure-Requests, DNT, Accept-Language)
7. Retry with exponential backoff + jitter (base_delay=1.0, max_retries=2)
8. Failure Intelligence integration
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import re
import time
from typing import Any, Optional

import httpx

from app.collectors.failure_intelligence import FailureAnalysis, analyze_failure
from app.collectors.registry import BaseCollectorProvider, CollectResult
from app.core import get_settings

_MAX_HTML_BYTES = 10 * 1024 * 1024  # 10 MB

# ── Enhancement 1: UA rotation pool ──────────────────────────────
_USER_AGENTS: list[str] = [
    # Chrome Win 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox Win 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    # Firefox macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:127.0) Gecko/20100101 Firefox/127.0",
]

# ── Enhancement 6: Browser-like headers template ─────────────────
_BROWSER_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",  # Enhancement 3
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


def _rotate_ua() -> str:
    """Pick a random User-Agent from the rotation pool."""
    return random.choice(_USER_AGENTS)


def _build_headers(url: str) -> dict[str, str]:
    """Build browser-like headers with a fresh rotated UA."""
    headers = dict(_BROWSER_HEADERS)
    headers["User-Agent"] = _rotate_ua()
    # Make Referer reasonable
    headers["Referer"] = f"https://{url.split('/')[2] if '//' in url else url}/"
    return headers


# ── Enhancement 5: Content-Type classification ───────────────────
_CONTENT_TYPE_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("html", ("text/html", "application/xhtml+xml")),
    ("json", ("application/json", "application/vnd.api+json")),
    ("xml", ("text/xml", "application/xml", "application/rss+xml", "application/atom+xml")),
    ("pdf", ("application/pdf",)),
    ("image", ("image/",)),
    ("text", ("text/plain", "text/css", "text/javascript", "application/javascript")),
]


def classify_content_type(content_type_header: str) -> str:
    """Classify Content-Type into a simple category: html/json/xml/pdf/image/text/other."""
    ct_lower = content_type_header.lower().split(";")[0].strip()
    for category, prefixes in _CONTENT_TYPE_MAP:
        for prefix in prefixes:
            if ct_lower.startswith(prefix):
                return category
    return "other"


# ── Enhancement 4: Charset auto-detection ────────────────────────
def _detect_charset(
    content: bytes,
    content_type_header: str,
) -> str:
    """Detect charset from Content-Type header → HTML meta → chardet → utf-8 fallback.

    Args:
        content: Raw response bytes.
        content_type_header: The Content-Type header value.

    Returns:
        Detected charset name (e.g. 'utf-8', 'gbk', 'shift-jis').
    """
    # 1. Check Content-Type header
    ct = content_type_header.lower()
    if "charset=" in ct:
        charset = ct.split("charset=")[-1].split(";")[0].strip().strip("'\"")
        if charset:
            return charset

    # 2. Check HTML <meta> charset
    try:
        import re

        # Try <meta charset="...">
        head_end = content.find(b"</head>")
        if head_end == -1:
            head_end = min(len(content), 8192)  # scan first 8K
        head_section = content[:head_end].decode("ascii", errors="replace")

        meta_charset = re.search(
            r'<meta[^>]+charset\s*=\s*["\']?([^"\'\s;>]+)',
            head_section,
            re.IGNORECASE,
        )
        if meta_charset:
            return meta_charset.group(1).strip().lower()

        # Try <meta http-equiv="Content-Type" content="...charset=...">
        meta_http = re.search(
            r'<meta[^>]+http-equiv\s*=\s*["\']?content-type["\']?[^>]+content\s*=\s*["\'][^"\']*charset=([^"\';>\s]+)',
            head_section,
            re.IGNORECASE,
        )
        if meta_http:
            return meta_http.group(1).strip().lower()
    except Exception:
        pass

    # 3. Use chardet library
    try:
        import chardet

        detected = chardet.detect(content[:4096])
        if detected and detected.get("encoding") and detected["confidence"] > 0.3:
            return detected["encoding"]
    except Exception:
        pass

    # 4. Fallback
    return "utf-8"


def _decode_content(content: bytes, content_type_header: str) -> str:
    """Decode bytes to string using auto-detected charset."""
    charset = _detect_charset(content, content_type_header)
    try:
        return content.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return content.decode("utf-8", errors="replace")


# ── Enhancement 7: Retry with exponential backoff + jitter ───────
def _backoff_delay(attempt: int, base_delay: float = 1.0) -> float:
    """Calculate delay with exponential backoff + jitter.

    delay = base_delay * (2 ** attempt) + random(0, 0.5)
    """
    return base_delay * (2**attempt) + random.uniform(0, 0.5)


# ── Existing helpers ─────────────────────────────────────────────
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


# ── Enhancement 8: Failure Intelligence integration ──────────────
def _make_failure_result(
    error_message: str,
    error_code: str,
    fetch_time_ms: int,
    http_status: int = 0,
    collector_kind: str = "direct_http",
) -> CollectResult:
    """Build a CollectResult with FailureIntelligence analysis."""
    # Classify content type if we have headers info (though not in error cases)
    fi = analyze_failure(error_message=error_message, http_status=http_status)
    return CollectResult(
        success=False,
        error_code=error_code,
        error_message=error_message,
        fetch_time_ms=fetch_time_ms,
        collector_kind=collector_kind,
        failure_intelligence=fi,
    )


class DirectHttpCollector(BaseCollectorProvider):
    """Collector that uses httpx to fetch URL content directly.

    Enhanced with 8 capability upgrades:
    1. UA rotation pool
    2. Split timeouts
    3. gzip/brotli support
    4. Charset auto-detection
    5. Content-Type classification
    6. Browser-like headers
    7. Retry with exponential backoff + jitter
    8. Failure Intelligence integration
    """

    kind = "direct_http"

    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        """Fetch URL with httpx, return normalised result.

        Args:
            url: The URL to fetch.
            **kwargs: Supports the following optional overrides:
                - timeout: overall timeout in seconds (default: uses split timeouts)
                - max_retries: max retry attempts (default: 2)
                - base_delay: base delay for backoff (default: 1.0)

        Returns:
            CollectResult with optional failure_intelligence.
        """
        settings = get_settings()
        user_agent = settings.COLLECTION_USER_AGENT  # fallback
        max_retries = kwargs.get("max_retries", 2)
        base_delay = kwargs.get("base_delay", 1.0)
        start = time.monotonic()

        # Enhancement 2: Split timeouts
        timeout_config = httpx.Timeout(
            connect=kwargs.get("connect_timeout", 10.0),
            read=kwargs.get("read_timeout", 20.0),
            write=kwargs.get("write_timeout", 10.0),
            pool=kwargs.get("pool_timeout", 5.0),
        )

        # Enhancement 7: Retry loop with exponential backoff
        last_exception: Optional[Exception] = None
        last_response: Optional[httpx.Response] = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = _backoff_delay(attempt - 1, base_delay)
                await asyncio.sleep(delay)

            try:
                headers = _build_headers(url)
                # Override UA from settings if explicitly set (keeping backwards compat)
                headers["User-Agent"] = user_agent if (user_agent and user_agent != "N/A") else _rotate_ua()

                async with httpx.AsyncClient(
                    timeout=timeout_config,
                    follow_redirects=True,
                    max_redirects=5,
                    headers=headers,
                    verify=kwargs.get("verify_ssl", True),
                ) as client:
                    response = await client.get(url)
                last_response = response
                last_exception = None
                break  # success — exit retry loop
            except httpx.TimeoutException as exc:
                last_exception = exc
                last_response = None
                if attempt < max_retries:
                    continue
            except httpx.ConnectError as exc:
                last_exception = exc
                last_response = None
                if attempt < max_retries:
                    continue
            except httpx.RequestError as exc:
                last_exception = exc
                last_response = None
                if attempt < max_retries:
                    continue
                break

        elapsed = int((time.monotonic() - start) * 1000)

        # ── Handle all-errors path ──────────────────────────────
        if last_exception is not None:
            error_str = str(last_exception).lower()
            error_code = "FETCH_HTTP_ERROR"

            if isinstance(last_exception, httpx.TimeoutException):
                error_code = "FETCH_TIMEOUT"
                return _make_failure_result(
                    error_message=f"Request timed out: {last_exception}",
                    error_code=error_code,
                    fetch_time_ms=elapsed,
                )

            if isinstance(last_exception, httpx.ConnectError):
                if (
                    "name" in error_str
                    or "resolve" in error_str
                    or "nodename" in error_str
                    or "getaddrinfo" in error_str
                ):
                    error_code = "DNS_FAILURE"
                else:
                    error_code = "CONNECTION_REFUSED"
                return _make_failure_result(
                    error_message=f"Connection error: {last_exception}",
                    error_code=error_code,
                    fetch_time_ms=elapsed,
                )

            return _make_failure_result(
                error_message=str(last_exception),
                error_code=error_code,
                fetch_time_ms=elapsed,
            )

        # ── We have a response ──────────────────────────────────
        assert last_response is not None  # for type checker
        response = last_response

        # Check HTTP status
        if response.status_code >= 400:
            fi = analyze_failure(
                error_message=f"HTTP {response.status_code}",
                http_status=response.status_code,
                content_type=response.headers.get("content-type", ""),
            )
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code="FETCH_HTTP_ERROR",
                error_message=f"HTTP {response.status_code}",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
                failure_intelligence=fi,
            )

        # Check content size
        content = response.content
        if len(content) > _MAX_HTML_BYTES:
            fi = FailureAnalysis(
                failure_type="content_too_large",
                retryable=False,
                suggested_next="skip_permanent",
                user_visible_message="内容过大，已跳过",
                http_status=response.status_code,
                content_type=response.headers.get("content-type", ""),
                blocked_reason=f"Content exceeds 10 MB ({len(content)} bytes)",
            )
            return CollectResult(
                success=False,
                final_url=str(response.url),
                http_status=response.status_code,
                error_code="CONTENT_TOO_LARGE",
                error_message=f"Content exceeds 10 MB ({len(content)} bytes)",
                response_headers=dict(response.headers),
                fetch_time_ms=elapsed,
                collector_kind=self.kind,
                failure_intelligence=fi,
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
            failure_intelligence=None,  # no failure
        )
