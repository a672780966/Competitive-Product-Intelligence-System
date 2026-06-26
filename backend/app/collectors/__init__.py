"""CPIS V1 — Web collectors package.

Existing collectors for raw fetch operations:
- HttpxCollector: static HTML fetcher
- PlaywrightCollector: JS-rendered page fetcher (lazy-imported)
- CollectorSelector: strategy pattern for selecting collector

New collector runtime (Node 5):
- CollectorRuntimeRegistry: maps collector kinds to executor providers
- DirectHttpCollector: httpx-based collector for the runtime
- PlaywrightRuntimeCollector: wraps existing PlaywrightCollector with graceful degradation
"""
from app.collectors.base import BaseCollector, CollectResult, FetchErrorCode
from app.collectors.httpx_collector import HttpxCollector
from app.collectors.selector import CollectorSelector
from app.collectors.registry import (
    BaseCollectorProvider,
    CollectorRuntimeRegistry,
    CollectResult as RegistryCollectResult,
    get_collector_registry,
)
from app.collectors.direct_http import DirectHttpCollector
from app.collectors.playwright_runtime import PlaywrightRuntimeCollector

# PlaywrightCollector is lazy-imported because playwright may not be installed.
# Import it via _get_playwright_collector() when actually needed.
_playwright_collector = None


def get_playwright_collector():
    """Lazy-import and return the PlaywrightCollector class."""
    global _playwright_collector
    if _playwright_collector is None:
        from app.collectors.playwright_collector import PlaywrightCollector
        _playwright_collector = PlaywrightCollector
    return _playwright_collector


__all__ = [
    "BaseCollector",
    "CollectResult",
    "FetchErrorCode",
    "HttpxCollector",
    "CollectorSelector",
    "get_playwright_collector",
    "BaseCollectorProvider",
    "CollectorRuntimeRegistry",
    "RegistryCollectResult",
    "DirectHttpCollector",
    "PlaywrightRuntimeCollector",
    "get_collector_registry",
]
