"""Provider Status API — returns current provider configuration and capabilities.

This endpoint enables frontend monitoring and debugging of which providers
are active (mock/stub vs real), what env keys may be missing, and which
collector runtimes are available.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core import get_settings
from app.providers.config import get_llm_provider_config, get_search_provider_config

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/provider-status")
async def get_provider_status() -> dict:
    """Return the current provider configuration and capabilities.

    Shows which search/LLM providers are active, whether real providers are
    enabled or the system is in mock/stub mode, missing environment variables,
    and the status of all collector runtimes.
    """
    settings = get_settings()
    search_config = get_search_provider_config()
    llm_config = get_llm_provider_config()

    search_provider = search_config.get("provider", "mock")
    llm_provider = llm_config.get("provider", "stub")

    missing_keys = []
    if llm_provider not in ("stub", "mock"):
        if not settings.LLM_API_KEY:
            missing_keys.append("LLM_API_KEY")
        if not settings.LLM_BASE_URL:
            missing_keys.append("LLM_BASE_URL")
        if not settings.LLM_MODEL:
            missing_keys.append("LLM_MODEL")

    return {
        "current_search_provider": search_provider,
        "current_llm_provider": llm_provider,
        "is_real_provider_enabled": (
            search_provider not in ("mock", "stub")
            or llm_provider not in ("stub", "mock")
        ),
        "is_mock_mode": (
            search_provider in ("mock", "stub")
            and llm_provider in ("stub", "mock")
        ),
        "search_provider_details": {
            "configured": search_provider,
            "real_available": ["duckduckgo"],
            "duckduckgo_verified": False,
        },
        "llm_provider_details": {
            "configured": llm_provider,
            "real_available": ["openai_compatible"],
            "has_api_key": bool(settings.LLM_API_KEY),
            "has_base_url": bool(settings.LLM_BASE_URL),
            "has_model": bool(settings.LLM_MODEL),
        },
        "missing_env_keys": missing_keys,
        "collector_runtimes": {
            "direct_http": {"enabled": True, "verified": True},
            "playwright": {"enabled": False, "verified": False},
            "scrapling": {"enabled": False, "verified": False},
            "crawl4ai": {"enabled": False, "verified": False},
            "rss": {"enabled": False, "verified": False},
            "pdf": {"enabled": False, "verified": False},
            "api": {"enabled": False, "verified": False},
        },
    }
