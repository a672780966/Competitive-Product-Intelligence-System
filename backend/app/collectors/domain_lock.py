"""
CPIS V1 — Domain concurrency limiter.

Ensures no more than N concurrent fetches to the same domain,
helping avoid aggressive crawling and IP-based rate limiting.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict


class DomainConcurrencyLimiter:
    """Limit concurrent requests per domain using semaphores.

    Usage::

        limiter = DomainConcurrencyLimiter(max_per_domain=2)
        async with limiter.limit("example.com"):
            await fetch(...)
    """

    def __init__(self, max_per_domain: int = 2) -> None:
        self._max_per_domain = max_per_domain
        self._semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(max_per_domain),
        )

    def limit(self, domain: str) -> asyncio.Semaphore:
        """Return a semaphore for the given domain — use with ``async with``."""
        return self._semaphores[domain]

    def release_all(self) -> None:
        """Clear all held semaphore state (for testing)."""
        self._semaphores.clear()
