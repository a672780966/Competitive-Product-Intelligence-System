# Real Provider Integration Plan

> **Status:** Planning — not yet scheduled  
> **Objective:** Transition from Mock/Stub providers to real LLM and Search integrations  
> **Owner:** TBD

---

## 1. Real LLM Integration

### Providers to implement

| Provider | Priority | Status | Notes |
|----------|----------|--------|-------|
| OpenAI (GPT-4o, GPT-4o-mini) | P0 | Reserved interface | Most common, good quality |
| Anthropic Claude (Sonnet, Haiku) | P1 | Reserved interface | Good for long-context extraction |
| Google Gemini (Pro, Flash) | P1 | Reserved interface | Cost-effective |
| DeepSeek | P2 | Reserved interface | Open-weight alternative |
| Qwen (Alibaba) | P2 | Reserved interface | Chinese-optimized |

### Implementation approach

1. **OpenAICompatibleProvider** already exists in `backend/app/providers/real_providers.py`
   - Need to verify it works end-to-end with real API calls
   - Currently only used internally — no tests with real keys
2. **Structured extraction prompts** are versioned in `backend/app/prompts/`
   - Validate output schema with real LLM responses
   - Handle malformed JSON / partial extraction gracefully
3. **Confidence scoring** needs real LLM calibration
   - Stub returns hardcoded 0.95 — real LLM needs proper scoring

### Required env keys

```
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

---

## 2. Real Search Provider Verification

### DuckDuckGo

- `DuckDuckGoSearchProvider` already implemented in `backend/app/providers/duckduckgo_provider.py`
- **Not verified** with real searches — needs integration test
- Known limitations:
  - Rate limiting (no official API, uses scrape)
  - Region/language filtering may be unreliable
  - No paid SLA

### Future search providers

| Provider | Priority | Status | Notes |
|----------|----------|--------|-------|
| SerpAPI | P1 | Reserved interface | Paid, reliable, many sources |
| OpenAI Search (web search) | P2 | Reserved interface | Upcoming feature |
| Bing Search API | P2 | Reserved interface | Azure marketplace |

---

## 3. Required Environment Keys

### Minimum for real LLM (OpenAI-compatible)

```bash
LLM_PROVIDER=openai
LLM_API_KEY=<your-api-key>
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### Optional for real search

```bash
SEARCH_PROVIDER=duckduckgo
# No keys needed for DuckDuckGo
# SERPAPI_API_KEY=<key>  # if using SerpAPI
```

---

## 4. Estimated Cost

### Per-discovery search (DuckDuckGo)

- **DuckDuckGo**: Free (scraping, rate-limited to ~1 req/s)
- **SerpAPI**: ~$0.01 per search (100 searches = $1)

### Per-extraction LLM call

| Model | Input tokens (~4K) | Output tokens (~1K) | Cost per extraction |
|-------|-------------------|---------------------|---------------------|
| GPT-4o-mini | $0.0006 | $0.0003 | ~$0.001 |
| GPT-4o | $0.01 | $0.03 | ~$0.04 |
| Claude Sonnet 4 | $0.008 | $0.04 | ~$0.05 |
| DeepSeek V3 | $0.0005 | $0.002 | ~$0.003 |

**Typical batch** (10 products, 1 extraction each):
- GPT-4o-mini: ~$0.01
- GPT-4o: ~$0.40

---

## 5. Test Standards

### Integration test requirements

Before enabling any real provider, the following tests must pass:

1. **Provider health check** — Real provider responds within 10s timeout
2. **Schema conformance** — Provider output matches Pydantic schema
3. **Error handling** — Network errors, auth failures, rate limits are handled gracefully
4. **Confidence calibration** — Stub-level confidence (0.7 threshold) works with real LLM output
5. **Retry policy** — 3 retries with exponential backoff works for transient failures
6. **Parallel safety** — Concurrent requests don't leak auth tokens or corrupt state

### CI gate

```bash
# Run all provider integration tests (requires env keys in CI secrets)
pytest tests/ -k "provider" -v

# Run overclaim protection (ensures docs stay honest)
pytest tests/test_overclaim_protection.py -v
```

---

## 6. Priority Recommendations

### Phase 1 (P0) — Quick wins

1. **Verify DuckDuckGo Search** — Run manual integration test, fix any issues
2. **Verify OpenAI extraction** — Set up real provider config, test with a single URL
3. **Update Provider Status API** — Show `is_real_provider_enabled=true` when configured
4. **Update documentation** — Mark real providers as verified in README

### Phase 2 (P1) — Production readiness

1. **Add comprehensive error handling** for real provider failures
2. **Integration tests in CI** with env keys from secrets
3. **Rate limiting and caching** for search provider
4. **Cost tracking** — Log per-extraction token usage and cost

### Phase 3 (P2) — Expansion

1. **Anthropic Claude provider** — Implement and test
2. **Google Gemini provider** — Implement and test
3. **SerpAPI integration** — Enable reliable search
4. **Web search via OpenAI** — If available

---

## Summary

| What | Status | Effort |
|------|--------|--------|
| DuckDuckGo code | ✅ Ready | 1-2 days to verify |
| OpenAI LLM code | ✅ Ready | 1-2 days to verify |
| Real provider tests | ❌ Missing | 2-3 days to write |
| CI integration | ❌ Missing | 1 day to set up |
| Documentation updates | 🔄 Done for v0.1.0 | Ongoing |
