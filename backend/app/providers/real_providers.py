"""Real provider factory functions — routes config to the correct implementation.

Provides create_real_search_provider() and create_real_llm_provider() factories
that read the active configuration and return the appropriate provider instance.
"""

from __future__ import annotations

import warnings

from app.core.logging import get_logger
from app.models.enums import SourceType
from app.providers.config import get_llm_provider_config, get_search_provider_config
from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider
from app.providers.interfaces import (
    AnalysisResult,
    LLMProvider,
    ModelProvider,
    SearchProvider,
    SearchResult,
)
from app.providers.mock_providers import MockSearchProvider, StubLLMProvider

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════
# Deprecated Stub Classes (kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════


class StubSearchProvider(SearchProvider):
    """DEPRECATED: Use DuckDuckGoSearchProvider or MockSearchProvider instead.

    Stub search provider — reads env config but does NOT call external APIs.
    Kept for backward compatibility only.
    """

    def __init__(self, provider_type: str = "stub"):
        warnings.warn(
            "StubSearchProvider is deprecated. "
            "Use DuckDuckGoSearchProvider or MockSearchProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._provider_type = provider_type

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        """Stub search — returns empty list."""
        return []


class StubModelProvider(ModelProvider):
    """DEPRECATED: Use StubLLMProvider or MockModelProvider instead.

    Stub model provider — reads env config but does NOT call any LLM API.
    Kept for backward compatibility only.
    """

    def __init__(self, provider_type: str = "stub"):
        warnings.warn(
            "StubModelProvider is deprecated. "
            "Use StubLLMProvider or MockModelProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._provider_type = provider_type

    async def analyze_source(
        self,
        search_result: SearchResult,
        *,
        brand: str | None = None,
        topic: str | None = None,
    ) -> AnalysisResult:
        """Stub analysis — returns generic result."""
        return AnalysisResult(
            source_type=SourceType.OTHER,
            relevance_score=0.5,
            reason="Stub analysis — replace with real implementation",
            suggested_title=search_result.title,
        )

    async def discover_sources(
        self,
        query: str,
        *,
        brand: str | None = None,
        topic: str | None = None,
        max_results: int = 10,
    ) -> list[AnalysisResult]:
        """Stub discovery — returns empty list."""
        return []


# ══════════════════════════════════════════════════════════════════
# Factory Functions
# ══════════════════════════════════════════════════════════════════


def create_real_search_provider() -> SearchProvider:
    """Create a search provider based on current configuration.

    Reads SEARCH_PROVIDER from settings and returns the appropriate
    implementation:
    - "duckduckgo" → DuckDuckGoSearchProvider
    - "mock" → MockSearchProvider
    - Others → MockSearchProvider (fallback)

    Returns:
        An instance of SearchProvider.
    """
    config = get_search_provider_config()
    provider_name = config.get("provider", "mock")

    logger.info("creating_search_provider", provider=provider_name)

    if provider_name == "duckduckgo":
        return DuckDuckGoSearchProvider()

    if provider_name in ("mock", "stub"):
        return MockSearchProvider()

    # Fallback
    logger.warning(
        "unknown_search_provider_falling_back",
        provider=provider_name,
    )
    return MockSearchProvider()


def create_real_llm_provider() -> LLMProvider:
    """Create an LLM provider based on current configuration.

    Reads LLM_PROVIDER from settings and returns the appropriate
    implementation:
    - "mock" / "stub" → StubLLMProvider
    - Others → StubLLMProvider (no real implementations yet)

    Returns:
        An instance of LLMProvider.
    """
    config = get_llm_provider_config()
    provider_name = config.get("provider", "mock")

    logger.info("creating_llm_provider", provider=provider_name)

    if provider_name in ("mock", "stub"):
        return StubLLMProvider()

    # For now, all real providers fall back to stub
    # Real implementations will be wired in a future phase
    logger.info(
        "llm_provider_not_implemented_using_stub",
        provider=provider_name,
    )
    return StubLLMProvider()
