"""Safe HTTP client -- enforces SSRF checks before every request.

- Wraps httpx.AsyncClient
- Checks URL safety via ``check_url_safe()`` before every request
- Follows redirects manually (max 5), re-checking each hop
- Streams response body, stops at 10 MB
- Only allows allowed Content-Types (text/html, application/xhtml+xml, etc.)
- Rejects non-http/https schemes
- Never uses follow_redirects=True
"""

from __future__ import annotations

from typing import Any

import httpx

from app.security.safe_url import check_url_safe

_DEFAULT_TIMEOUT: int = 30
_DEFAULT_MAX_REDIRECTS: int = 5
_DEFAULT_MAX_CONTENT_BYTES: int = 10 * 1024 * 1024  # 10 MB

_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({
    "text/html",
    "application/xhtml+xml",
    "application/xml",
    "text/plain",
})


class SafeHttpxClient:
    """Async HTTP client with mandatory SSRF protection.

    Wraps ``httpx.AsyncClient`` and enforces URL safety checks
    (via :func:`check_url_safe`) before every request and each
    redirect hop.

    Usage::

        client = SafeHttpxClient(timeout=20)
        response = await client.get("https://example.com/page")
    """

    def __init__(
        self,
        timeout: int = _DEFAULT_TIMEOUT,
        max_redirects: int = _DEFAULT_MAX_REDIRECTS,
        max_content_bytes: int = _DEFAULT_MAX_CONTENT_BYTES,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialise the safe HTTP client.

        Args:
            timeout: Request timeout in seconds.
            max_redirects: Maximum number of redirects to follow.
            max_content_bytes: Maximum response body size in bytes.
            headers: Default headers to include with every request.
        """
        self._timeout = timeout
        self._max_redirects = max_redirects
        self._max_content_bytes = max_content_bytes
        self._default_headers = headers or {}

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform a safe GET request.

        Args:
            url: The target URL.
            **kwargs: Additional arguments forwarded to httpx.

        Returns:
            An ``httpx.Response`` with fully read content.

        Raises:
            ValueError: If the URL is unsafe, content type is rejected,
                or the response body exceeds the size limit.
            httpx.RequestError: On network / timeout errors.
        """
        return await self.safe_request("GET", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform a safe HEAD request.

        Args:
            url: The target URL.
            **kwargs: Additional arguments forwarded to httpx.

        Returns:
            An ``httpx.Response`` with fully read content (small for HEAD).

        Raises:
            ValueError: If the URL is unsafe or content type is rejected.
            httpx.RequestError: On network / timeout errors.
        """
        return await self.safe_request("HEAD", url, **kwargs)

    async def safe_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform a safe HTTP request with SSRF protection.

        This is the core method that:
        1. Validates the URL for SSRF safety
        2. Makes the request with manual redirect handling
        3. Re-checks every redirect target
        4. Validates Content-Type against the allowlist
        5. Streams the response body with a size limit

        Args:
            method: HTTP method (GET, HEAD, etc.).
            url: The target URL.
            **kwargs: Additional arguments forwarded to httpx.

        Returns:
            An ``httpx.Response`` with fully read content.

        Raises:
            ValueError: If the URL is unsafe, the content type is not
                allowed, or the response body exceeds ``max_content_bytes``.
            httpx.RequestError: On network / timeout / protocol errors.
        """
        # 1. Check initial URL safety
        result = await check_url_safe(url)
        if not result.safe:
            raise ValueError(f"SSRF blocked: {result.reason}")

        # Merge default headers
        headers = {**self._default_headers, **kwargs.pop("headers", {})}

        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
        ) as client:
            current_url: str = url
            current_method: str = method

            for redirect_count in range(self._max_redirects + 1):
                # Re-check each hop's URL (first iteration checks the original)
                result = await check_url_safe(current_url)
                if not result.safe:
                    raise ValueError(
                        f"SSRF blocked{' during redirect' if redirect_count > 0 else ''}: "
                        f"{result.reason}",
                    )

                async with client.stream(
                    current_method,
                    current_url,
                    headers=headers,
                    **kwargs,
                ) as response:
                    # Follow redirects manually
                    if response.status_code in (301, 302, 303, 307, 308):
                        if redirect_count >= self._max_redirects:
                            raise ValueError(
                                f"Too many redirects (> {self._max_redirects})",
                            )

                        location = response.headers.get("Location")
                        if not location:
                            # No Location header -- return the redirect response as-is
                            return _finish_response(response, b"")

                        current_url = str(httpx.URL(location))
                        # 303 always changes method to GET per HTTP spec
                        if response.status_code == 303:
                            current_method = "GET"
                        # 301/302/307 preserve the original method
                        continue  # Exit stream context without reading body

                    # -- Final response: validate and read body --

                    # 4. Content-Type allowlist check
                    raw_ct = (
                        response.headers.get("content-type", "").split(";")[0].strip()
                    )
                    if raw_ct and raw_ct not in _ALLOWED_CONTENT_TYPES:
                        raise ValueError(
                            f"Content type not allowed: {raw_ct}",
                        )

                    # 5. Streaming read with size limit
                    chunks: list[bytes] = []
                    total: int = 0
                    async for chunk in response.aiter_bytes():
                        chunks.append(chunk)
                        total += len(chunk)
                        if total > self._max_content_bytes:
                            raise ValueError(
                                f"Response body exceeds "
                                f"{self._max_content_bytes} bytes limit",
                            )

                    full_content = b"".join(chunks)
                    return _finish_response(response, full_content)

            # Exceeded max_redirects without returning
            raise ValueError(f"Too many redirects (> {self._max_redirects})")


def _finish_response(
    response: httpx.Response,
    content: bytes,
) -> httpx.Response:
    """Construct a new ``httpx.Response`` with the content populated.

    The streaming response from ``client.stream()`` does not have
    ``.content`` set; this helper builds a proper response object.
    """
    return httpx.Response(
        status_code=response.status_code,
        headers=response.headers,
        content=content,
        request=response.request,
    )
