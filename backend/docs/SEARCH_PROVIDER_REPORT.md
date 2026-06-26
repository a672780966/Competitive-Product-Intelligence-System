# Search Provider Report

## Summary

| Item | Value |
|---|---|
| **Phase** | IV |
| **Status** | ✅ Complete |
| **Interfaces** | `SearchProvider` (ABC) |
| **Implementations** | 5 (1 real + 4 reserved) |
| **Default** | `MockSearchProvider` |
| **Real Provider** | `DuckDuckGoSearchProvider` |

## Implementations

### 1. MockSearchProvider
- **File:** `app/providers/mock_providers.py`
- **Purpose:** Testing & development
- **Network:** None (returns fixture data)
- **Fixtures:** 8 predefined search results for "xiaomi 14 ultra"
- **Methods:** `search(query, max_results=10, language="zh-CN", brand=None, topic=None)`

### 2. DuckDuckGoSearchProvider ✅
- **File:** `app/providers/duckduckgo_provider.py`
- **Purpose:** Free production search
- **Network:** HTTP POST to `https://html.duckduckgo.com/html/`
- **Auth:** None (free, no API key)
- **Library:** `httpx`
- **Max Results:** 30 (DDG page limit)
- **Timeout:** 15 seconds (configurable)
- **Features:**
  - Language-to-region code mapping
  - HTML parsing with regex fallback
  - Redirect URL extraction
  - Error handling (timeout, HTTP errors)

### 3. OpenAISearchProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 4. GeminiSearchProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 5. ClaudeSearchProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 6. SerpAPISearchProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

## Factory Routing

```python
def create_real_search_provider() -> SearchProvider:
    """
    - "duckduckgo" → DuckDuckGoSearchProvider
    - "mock" / "stub" → MockSearchProvider
    - Others → MockSearchProvider (fallback)
    """
```

## Test Coverage

| Test Class | Tests | Status |
|---|---|---|
| `TestSearchProviderInterface` | 5 | ✅ Passing |
| `TestMockCandidateCreation` | 3 | ✅ Passing |
| `TestReservedSearchProviders` | 3 | ✅ Passing |
| `TestFactoryRouting` (search) | 2 | ✅ Passing |
