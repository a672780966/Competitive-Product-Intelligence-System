"""CPIS V1 — Web collectors package."""

from app.collectors.base import BaseCollector, CollectResult, FetchErrorCode
from app.collectors.httpx_collector import HttpxCollector
from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.selector import CollectorSelector

__all__ = [
    "BaseCollector",
    "CollectResult",
    "FetchErrorCode",
    "HttpxCollector",
    "PlaywrightCollector",
    "CollectorSelector",
]
