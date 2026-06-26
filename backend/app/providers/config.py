"""Provider configuration — reads from env / Settings.

Provides factory configuration functions that return typed config dicts
for search providers, LLM providers, and caching. No direct API calls here.
"""

from __future__ import annotations

from app.core import get_settings


def get_search_provider_config() -> dict:
    """Return search provider configuration from Settings.

    Returns:
        dict with:
        - provider: str (e.g. "duckduckgo", "mock", "bing", "serpapi")
    """
    settings = get_settings()
    return {
        "provider": settings.SEARCH_PROVIDER,
    }


def get_llm_provider_config() -> dict:
    """Return LLM provider configuration from Settings.

    Returns:
        dict with:
        - provider: str (e.g. "openai", "mock", "anthropic", "deepseek", "qwen")
        - api_key: str
        - base_url: str
        - model: str
    """
    settings = get_settings()
    return {
        "provider": settings.LLM_PROVIDER,
        "api_key": settings.LLM_API_KEY,
        "base_url": settings.LLM_BASE_URL,
        "model": settings.LLM_MODEL,
    }


def get_cache_config() -> dict:
    """Return cache configuration from Settings.

    Returns:
        dict with:
        - enabled: bool
        - ttl_seconds: int
    """
    settings = get_settings()
    return {
        "enabled": settings.CACHE_ENABLED,
        "ttl_seconds": settings.CACHE_TTL_SECONDS,
    }
