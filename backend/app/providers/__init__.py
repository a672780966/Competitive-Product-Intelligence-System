"""CPIS V1 — Provider layer for search, LLM, and model providers.

Provides abstract interfaces, mock implementations, real provider factories,
and configuration helpers for the AI Discovery Provider Layer.

Contains:
- Interfaces: SearchProvider, ModelProvider, LLMProvider, dataclasses, ranking
- Mocks: MockSearchProvider, MockModelProvider, StubLLMProvider
- Real: DuckDuckGoSearchProvider, factory functions
- Reserved: Placeholder classes for future providers
- Config: Config helpers for provider selection
"""

from __future__ import annotations

from app.providers.config import (
    get_cache_config,
    get_llm_provider_config,
    get_search_provider_config,
)
from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider
from app.providers.interfaces import (
    AnalysisResult,
    ClassifiedResult,
    ExtractionResult,
    HIGH_RISK_DOMAINS,
    LLMProvider,
    ModelProvider,
    REVIEW_DOMAIN_KEYWORDS,
    SOURCE_TYPE_SCORE,
    SOCIAL_DOMAIN_KEYWORDS,
    SearchProvider,
    SearchResult,
    assess_risk_level,
    rank_candidates,
    recommend_collector,
)
from app.providers.mock_providers import (
    FIXTURE_ANALYSIS_RESULTS,
    FIXTURE_SEARCH_RESULTS,
    MockModelProvider,
    MockSearchProvider,
    StubLLMProvider,
    create_mock_candidates,
    create_mock_model_provider,
    create_mock_search_provider,
    create_stub_llm_provider,
)
from app.providers.real_providers import (
    StubModelProvider,
    StubSearchProvider,
    create_real_llm_provider,
    create_real_search_provider,
)
from app.providers.reserved_providers import (
    ClaudeLLMProvider,
    ClaudeSearchProvider,
    DeepSeekLLMProvider,
    GeminiLLMProvider,
    GeminiSearchProvider,
    OpenAILLMProvider,
    OpenAISearchProvider,
    QwenLLMProvider,
    SerpAPISearchProvider,
)

__all__ = [
    # Interfaces
    "SearchProvider",
    "ModelProvider",
    "LLMProvider",
    "SearchResult",
    "AnalysisResult",
    "ClassifiedResult",
    "ExtractionResult",
    "assess_risk_level",
    "recommend_collector",
    "rank_candidates",
    "SOURCE_TYPE_SCORE",
    "HIGH_RISK_DOMAINS",
    "SOCIAL_DOMAIN_KEYWORDS",
    "REVIEW_DOMAIN_KEYWORDS",
    # Mock providers
    "MockSearchProvider",
    "MockModelProvider",
    "StubLLMProvider",
    "FIXTURE_SEARCH_RESULTS",
    "FIXTURE_ANALYSIS_RESULTS",
    "create_mock_search_provider",
    "create_mock_model_provider",
    "create_stub_llm_provider",
    "create_mock_candidates",
    # Real providers & factories
    "DuckDuckGoSearchProvider",
    "create_real_search_provider",
    "create_real_llm_provider",
    "StubSearchProvider",
    "StubModelProvider",
    # Reserved providers
    "OpenAISearchProvider",
    "GeminiSearchProvider",
    "ClaudeSearchProvider",
    "SerpAPISearchProvider",
    "OpenAILLMProvider",
    "GeminiLLMProvider",
    "ClaudeLLMProvider",
    "DeepSeekLLMProvider",
    "QwenLLMProvider",
    # Config
    "get_search_provider_config",
    "get_llm_provider_config",
    "get_cache_config",
]
