"""Reserved provider stubs — placeholder classes for future implementation.

These classes define the reserved names for real provider implementations.
Each raises NotImplementedError if instantiated or called.
They will be replaced with real implementations in a future phase.
"""

from __future__ import annotations

from app.providers.interfaces import (
    ClassifiedResult,
    ExtractionResult,
    LLMProvider,
    SearchProvider,
    SearchResult,
)


# ══════════════════════════════════════════════════════════════════
# Reserved Search Providers
# ══════════════════════════════════════════════════════════════════


class OpenAISearchProvider(SearchProvider):
    """Reserved for OpenAI web search (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "OpenAISearchProvider is reserved for future implementation. "
            "Use DuckDuckGoSearchProvider or MockSearchProvider instead."
        )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError(
            "OpenAISearchProvider is not yet implemented."
        )


class GeminiSearchProvider(SearchProvider):
    """Reserved for Google Gemini web search (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "GeminiSearchProvider is reserved for future implementation. "
            "Use DuckDuckGoSearchProvider or MockSearchProvider instead."
        )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError(
            "GeminiSearchProvider is not yet implemented."
        )


class ClaudeSearchProvider(SearchProvider):
    """Reserved for Anthropic Claude web search (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "ClaudeSearchProvider is reserved for future implementation. "
            "Use DuckDuckGoSearchProvider or MockSearchProvider instead."
        )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError(
            "ClaudeSearchProvider is not yet implemented."
        )


class SerpAPISearchProvider(SearchProvider):
    """Reserved for SerpAPI search provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "SerpAPISearchProvider is reserved for future implementation. "
            "Use DuckDuckGoSearchProvider or MockSearchProvider instead."
        )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError(
            "SerpAPISearchProvider is not yet implemented."
        )


# ══════════════════════════════════════════════════════════════════
# Reserved LLM Providers
# ══════════════════════════════════════════════════════════════════


class OpenAILLMProvider(LLMProvider):
    """Reserved for OpenAI LLM provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "OpenAILLMProvider is reserved for future implementation. "
            "Use StubLLMProvider or MockModelProvider instead."
        )

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        raise NotImplementedError(
            "OpenAILLMProvider is not yet implemented."
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "OpenAILLMProvider is not yet implemented."
        )


class GeminiLLMProvider(LLMProvider):
    """Reserved for Google Gemini LLM provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "GeminiLLMProvider is reserved for future implementation. "
            "Use StubLLMProvider or MockModelProvider instead."
        )

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        raise NotImplementedError(
            "GeminiLLMProvider is not yet implemented."
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "GeminiLLMProvider is not yet implemented."
        )


class ClaudeLLMProvider(LLMProvider):
    """Reserved for Anthropic Claude LLM provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "ClaudeLLMProvider is reserved for future implementation. "
            "Use StubLLMProvider or MockModelProvider instead."
        )

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        raise NotImplementedError(
            "ClaudeLLMProvider is not yet implemented."
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "ClaudeLLMProvider is not yet implemented."
        )


class DeepSeekLLMProvider(LLMProvider):
    """Reserved for DeepSeek LLM provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "DeepSeekLLMProvider is reserved for future implementation. "
            "Use StubLLMProvider or MockModelProvider instead."
        )

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        raise NotImplementedError(
            "DeepSeekLLMProvider is not yet implemented."
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "DeepSeekLLMProvider is not yet implemented."
        )


class QwenLLMProvider(LLMProvider):
    """Reserved for Alibaba Qwen LLM provider (future)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "QwenLLMProvider is reserved for future implementation. "
            "Use StubLLMProvider or MockModelProvider instead."
        )

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        raise NotImplementedError(
            "QwenLLMProvider is not yet implemented."
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError(
            "QwenLLMProvider is not yet implemented."
        )
