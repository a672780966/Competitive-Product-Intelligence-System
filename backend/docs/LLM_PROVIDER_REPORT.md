# LLM Provider Report

## Summary

| Item | Value |
|---|---|
| **Phase** | IV |
| **Status** | ✅ Complete |
| **Interfaces** | `LLMProvider` (ABC) + `ModelProvider` (legacy ABC) |
| **Implementations** | 6 (1 stub + 5 reserved) |
| **Default** | `StubLLMProvider` |
| **Dataclasses** | `ClassifiedResult`, `ExtractionResult`, `AnalysisResult` |

## Implementations

### 1. StubLLMProvider ✅
- **File:** `app/providers/mock_providers.py`
- **Purpose:** Testing & development
- **Network:** None (URL-pattern-based classification)
- **Methods:**
  - `classify(title, snippet, url, brand, topic) → ClassifiedResult`
  - `extract(content, url, brand, topic) → ExtractionResult`
- **Classification Logic:**
  - `mi.com` / `xiaomi` domains → `OFFICIAL_HOMEPAGE` (score 0.95)
  - `zhihu` / `tieba` / `xiaohongshu` domains → `FORUM` (score 0.40)
  - `review` / `ithome` / `news` domains → `REVIEW` (score 0.75)
  - All others → `OTHER` (score 0.30)
- **Extraction:** Returns empty `ExtractionResult` with a note

### 2. OpenAILLMProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 3. GeminiLLMProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 4. ClaudeLLMProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 5. DeepSeekLLMProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

### 6. QwenLLMProvider 🔜
- **File:** `app/providers/reserved_providers.py`
- **Status:** Reserved — raises `NotImplementedError`

## Factory Routing

```python
def create_real_llm_provider() -> LLMProvider:
    """
    - "mock" / "stub" → StubLLMProvider
    - Others → StubLLMProvider (fallback — no real impls yet)
    """
```

## Test Coverage

| Test Class | Tests | Status |
|---|---|---|
| `TestLLMProvider` | 8 | ✅ Passing |
| `TestModelProviderInterface` | 4 | ✅ Passing |
| `TestReservedLLMProviders` | 2 | ✅ Passing |
| `TestFactoryRouting` (LLM) | 2 | ✅ Passing |
