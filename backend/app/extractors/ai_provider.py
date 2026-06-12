"""
CPIS V1 — AI Provider Adapter.

Abstracts LLM inference behind a common interface.
Supports OpenAI-compatible APIs (OpenAI, Azure, local models, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIProviderError(Exception):
    """Raised when the AI provider returns an error."""
    pass


class AIProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request and return the text response."""
        ...


class OpenAICompatibleProvider(AIProvider):
    """Provider for OpenAI-compatible chat completion APIs.

    Works with: OpenAI, Azure OpenAI, Ollama, vLLM, LocalAI, etc.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        default_model: str = "gpt-4o",
        timeout: int = 60,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.LLM_API_KEY
        self._base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self._default_model = default_model or settings.LLM_MODEL
        self._timeout = timeout

        if not self._base_url:
            self._base_url = "https://api.openai.com/v1"

    @property
    def model(self) -> str:
        return self._default_model

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion and return the response text."""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model or self._default_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(
            "llm_request",
            model=body["model"],
            url=url,
            system_len=len(system_prompt),
            user_len=len(user_prompt),
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            raise AIProviderError("LLM request timed out")
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(f"LLM HTTP {exc.response.status_code}: {exc.response.text[:500]}")
        except httpx.RequestError as exc:
            raise AIProviderError(f"LLM request failed: {exc}")

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Unexpected LLM response format: {exc}")

        if not text:
            raise AIProviderError("LLM returned empty response")

        logger.info("llm_response", model=body["model"], response_len=len(text))
        return text


def create_provider() -> AIProvider:
    """Factory: return the configured AI provider."""
    return OpenAICompatibleProvider()
