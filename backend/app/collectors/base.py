"""
CPIS V1 — Base collector interface and shared types.

All collectors must implement ``fetch()`` and return a ``CollectResult``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class FetchErrorCode(str, Enum):
    """Standardized fetch error codes."""

    FETCH_TIMEOUT = "FETCH_TIMEOUT"
    FETCH_HTTP_ERROR = "FETCH_HTTP_ERROR"
    CONTENT_TOO_LARGE = "CONTENT_TOO_LARGE"
    DNS_FAILURE = "DNS_FAILURE"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    PLAYWRIGHT_ERROR = "PLAYWRIGHT_ERROR"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"


@dataclass
class CollectResult:
    """Normalised result from a collector."""

    success: bool
    final_url: str = ""
    http_status: int = 0
    page_title: str = ""
    raw_html: bytes = b""
    response_headers: dict[str, str] = field(default_factory=dict)
    content_hash: str = ""
    error_code: FetchErrorCode | None = None
    error_message: str = ""
    fetch_time_ms: int = 0
    used_playwright: bool = False


class BaseCollector(ABC):
    """Abstract collector — every collector must implement ``fetch()``."""

    @abstractmethod
    async def fetch(self, url: str, *, timeout: int = 20) -> CollectResult:
        """Fetch a URL and return a normalised CollectResult."""
        ...
