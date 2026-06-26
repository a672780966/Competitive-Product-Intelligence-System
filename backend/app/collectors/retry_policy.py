"""RetryPolicy — per-collector-kind retry configuration.

Provides default retry counts per collector kind, with the ability
to override individual values and fallback to the global
COLLECTION_MAX_RETRIES setting.
"""
from __future__ import annotations

from typing import Any

from app.core import get_settings

_DEFAULT_RETRIES: dict[str, int] = {
    "direct_http": 3,
    "playwright": 1,
    "scrapling": 2,
    "crawl4ai": 1,
    "blocked": 0,
    "rss": 3,
    "pdf": 2,
    "api": 3,
}


class RetryPolicy:
    """Determine max retries for a given collector kind.

    Args:
        overrides: Optional dict of per-kind retry overrides.
    """

    def __init__(self, overrides: dict[str, int] | None = None) -> None:
        self._overrides: dict[str, int] = overrides or {}

    def get_max_retries(self, kind: str) -> int:
        """Return the maximum retry count for a given collector kind.

        Priority:
        1. Explicit override (passed to constructor)
        2. Default for the kind
        3. Global COLLECTION_MAX_RETRIES setting
        4. 1 (ultimate fallback)
        """
        if kind in self._overrides:
            return self._overrides[kind]

        if kind in _DEFAULT_RETRIES:
            return _DEFAULT_RETRIES[kind]

        try:
            settings = get_settings()
            return settings.COLLECTION_MAX_RETRIES
        except Exception:
            return 1
