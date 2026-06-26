# Discovery Provider Architecture

## Overview

The Discovery Provider Layer provides a pluggable architecture for source discovery in the CPIS V1 system. It allows the system to search for competitive intelligence sources and classify them using AI-powered analysis, all through well-defined interfaces that can be swapped between mock (testing), free (DuckDuckGo), and premium (OpenAI, Gemini, Claude, etc.) implementations.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DiscoveryService                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Cache    │  │ Search   │  │ LLM      │  │ SearchHistory     │  │
│  │ Service  │→ │ Provider │→ │ Provider │→ │ Repository        │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘  │
│                                          ↓                         │
│                                    UsageService                    │
│                                    (recording)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Two-Track Provider System

### Track 1: Original (Legacy) — ModelProvider + SearchProvider

Used by the original `DiscoveryService` implementation. `ModelProvider` wraps both search and analysis.

### Track 2: Refactored (Current) — LLMProvider + SearchProvider

Used by the refactored `DiscoveryService`. `LLMProvider` separates classification (`classify()`) from extraction (`extract()`).

## Provider Types

| Provider | Interface | Current Implementation |
|---|---|---|
| Search | `SearchProvider` | `MockSearchProvider`, `DuckDuckGoSearchProvider` |
| LLM/Analysis | `LLMProvider` | `StubLLMProvider` |
| Model (legacy) | `ModelProvider` | `MockModelProvider` |

## Reserved Providers

Placeholder classes for 9 future implementations across 4 search + 5 LLM providers. All raise `NotImplementedError` on instantiation.

### Search Providers
- `DuckDuckGoSearchProvider` — ✅ Implemented (free, no API key)
- `OpenAISearchProvider` — 🔜 Reserved
- `GeminiSearchProvider` — 🔜 Reserved
- `ClaudeSearchProvider` — 🔜 Reserved
- `SerpAPISearchProvider` — 🔜 Reserved

### LLM Providers
- `StubLLMProvider` — ✅ Implemented (mock/fixture)
- `OpenAILLMProvider` — 🔜 Reserved
- `GeminiLLMProvider` — 🔜 Reserved
- `ClaudeLLMProvider` — 🔜 Reserved
- `DeepSeekLLMProvider` — 🔜 Reserved
- `QwenLLMProvider` — 🔜 Reserved

## Data Flow

```
1. DiscoveryService.create_session(request)
2.   → Create SourceDiscoverySession (status=running)
3.   → _run_discovery()
4.     → SearchCacheService.get()          [cache check]
5.     → SearchProvider.search()           [if cache miss]
6.     → SearchCacheService.set()          [cache update]
7.     → LLMProvider.classify()            [per result]
8.     → assess_risk_level() + recommend_collector()
9.     → rank_candidates()                 [sorted by desirability]
10.    → DiscoveryRepository.bulk_create_candidates()
11.    → UsageService.record_usage()       [best-effort]
12.    → SearchHistoryRepository.record()  [best-effort]
13.  → Update session status (completed/failed)
```

## Configuration

Provider selection is managed via configuration settings (see `providers/config.py`):

```python
# Example config access
from app.providers.config import get_search_provider_config, get_llm_provider_config

search_config = get_search_provider_config()   # {"provider": "duckduckgo", ...}
llm_config = get_llm_provider_config()          # {"provider": "mock", ...}
```

## Testing

All providers have mock/stub implementations that return fixture data with no network calls. Tests use:
- `MockSearchProvider` — returns predefined search results
- `StubLLMProvider` — classifies based on URL pattern matching
- `SearchCacheService` — in-memory TTL-based cache (configurable)
