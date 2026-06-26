"""DuckDuckGo search provider — free, no API key needed.

Uses httpx to query DuckDuckGo's HTML search endpoint directly.
No external SDK required.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.logging import get_logger
from app.providers.interfaces import SearchProvider, SearchResult

logger = get_logger(__name__)

# DuckDuckGo HTML search URL
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"

# Default user agent to avoid being blocked
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Timeout for HTTP requests
DEFAULT_TIMEOUT_SECONDS = 15


class DuckDuckGoSearchProvider(SearchProvider):
    """Search provider that queries DuckDuckGo's free HTML endpoint.

    No API key needed. Uses httpx for HTTP requests.
    Respects max_results and language parameters.
    """

    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent
        self._client = client

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        """Execute a search via DuckDuckGo HTML endpoint.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return (max 30).
            language: Language hint (used in query refinement).
            brand: Optional brand context (not sent to DDG).
            topic: Optional topic context (not sent to DDG).

        Returns:
            List of SearchResult objects.
        """
        if not query or not query.strip():
            return []

        max_results = min(max_results, 30)  # DDG returns ~30 per page
        results: list[SearchResult] = []
        client = self._client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
        )

        try:
            # Build form data for DDG HTML search
            form_data: dict[str, str] = {
                "q": query,
                "kl": self._language_to_region(language),
            }

            logger.debug(
                "ddg_search_request",
                query=query,
                max_results=max_results,
                language=language,
            )

            response = await client.post(
                DDG_SEARCH_URL,
                data=form_data,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                follow_redirects=True,
            )
            response.raise_for_status()

            # Parse HTML results
            results = self._parse_html_results(response.text, max_results)

            logger.debug(
                "ddg_search_response",
                query=query,
                result_count=len(results),
            )

        except httpx.TimeoutException:
            logger.warning("ddg_search_timeout", query=query)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "ddg_search_http_error",
                query=query,
                status_code=exc.response.status_code,
            )
        except Exception as exc:
            logger.error("ddg_search_error", query=query, error=str(exc))
        finally:
            if self._client is None:
                await client.aclose()

        return results

    def _parse_html_results(
        self, html: str, max_results: int,
    ) -> list[SearchResult]:
        """Parse DDG HTML search results page.

        Extracts title, URL, and snippet from result elements.
        """
        results: list[SearchResult] = []

        # Find all result blocks — they're in <div> with class containing "result"
        # We use regex to find result blocks more reliably than full HTML parsing
        result_blocks = re.findall(
            r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="[^"]*result|$)',
            html,
            re.DOTALL,
        )

        # If regex didn't work well, try alternative parsing
        if not result_blocks:
            # Fallback: use simpler link-based parsing
            result_blocks = self._fallback_parse(html)

        for block in result_blocks[:max_results]:
            result = self._parse_single_result(block)
            if result is not None:
                results.append(result)
                if len(results) >= max_results:
                    break

        return results

    def _parse_single_result(self, html_block: str) -> SearchResult | None:
        """Parse a single DDG result block into a SearchResult."""
        # Extract title from <a> tag
        title_match = re.search(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>',
            html_block,
            re.DOTALL,
        )
        if not title_match:
            # Try alternate title container
            title_match = re.search(
                r'<a[^>]*>(.*?)</a>',
                html_block,
                re.DOTALL,
            )

        if not title_match:
            return None

        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        if not title:
            return None

        # Extract URL
        url_match = re.search(
            r'<a[^>]*href="(https?://[^"]+)"',
            html_block,
        )
        if not url_match:
            url_match = re.search(r'<a[^>]*href="([^"]+)"', html_block)
        if not url_match:
            return None

        url = url_match.group(1)
        # DDG wraps URLs in redirect — extract original
        if "uddg=" in url:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "uddg" in params:
                url = params["uddg"][0]

        # Extract snippet
        snippet_match = re.search(
            r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            html_block,
            re.DOTALL,
        )
        snippet = ""
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()

        return SearchResult(
            title=title,
            url=url,
            snippet=snippet,
            source="duckduckgo",
        )

    def _fallback_parse(self, html: str) -> list[str]:
        """Fallback parsing when standard result blocks aren't found."""
        # Extract all link+text combinations
        blocks: list[str] = []
        # Find all <h2> or result title elements followed by links
        pattern = re.findall(
            r'<h2[^>]*>(.*?)</h2>',
            html,
            re.DOTALL,
        )
        if pattern:
            return pattern
        # Last resort
        return []

    @staticmethod
    def _language_to_region(language: str) -> str:
        """Convert language code to DDG region code."""
        region_map: dict[str, str] = {
            "zh-CN": "cn-zh",
            "zh": "cn-zh",
            "en-US": "us-en",
            "en": "wt-wt",
            "ja": "jp-jp",
            "ko": "kr-kr",
        }
        return region_map.get(language, "wt-wt")
