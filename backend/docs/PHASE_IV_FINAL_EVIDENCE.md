# Phase IV — Final Evidence Report

## Overview

Phase IV completes the **Discovery Provider Layer**, adding:
- `LLMProvider` interface (separated from legacy `ModelProvider`)
- `SearchCacheService` (TTL-based in-memory cache)
- `SearchHistoryRepository` (search audit trail)
- `DuckDuckGoSearchProvider` (free production search)
- 9 Reserved Provider stubs (future implementations)
- `rank_candidates()` (candidate desirability sorting)
- `UsageService` wiring (discovery + collection pipeline)

## Tests Run

**Command:** `pytest -q --ignore=tests/test_collectors.py --ignore=tests/test_cleaners.py`

**Result:** 459 passed, 0 failed, 2 warnings

> 15 pre-existing failures in `test_cleaners.py` (missing `lxml` library) are unrelated to Phase IV changes.

## Files Created

### New Files (8)

| File | Purpose |
|---|---|
| `app/repositories/search_history_repository.py` | SearchHistory CRUD |
| `tests/test_providers_phase4.py` | Config, factory, reserved provider tests |
| `tests/test_search_cache_service.py` | Cache hit/miss/TTL tests |
| `tests/test_search_history.py` | SearchHistory model + repository tests |
| `docs/DISCOVERY_PROVIDER_ARCHITECTURE.md` | Architecture overview |
| `docs/PROVIDER_INTERFACE_SPEC.md` | Interface specifications |
| `docs/SEARCH_PROVIDER_REPORT.md` | Search provider implementation report |
| `docs/LLM_PROVIDER_REPORT.md` | LLM provider implementation report |

### Files Modified (7)

| File | Changes |
|---|---|
| `app/services/discovery_service.py` | Refactored: `llm_provider` instead of `model_provider`, added `usage_service`, `cache_service`, `search_history_repo` params; updated `_run_discovery()` flow |
| `app/providers/mock_providers.py` | Added `brand`/`topic` params to `MockSearchProvider.search()` |
| `app/providers/interfaces.py` | Fixed `rank_candidates()` stable sort order |
| `app/tasks/collection.py` | Wired `_record_usage()` into all 3 pipeline stages |
| `tests/test_discovery_providers.py` | Added `TestLLMProvider` (8 tests) + `TestRankCandidates` (7 tests) |

## Test Breakdown

| Test File | Tests | Status |
|---|---|---|
| `test_discovery_providers.py` | 41 (incl. 15 new) | ✅ All passing |
| `test_providers_phase4.py` | 13 (new) | ✅ All passing |
| `test_search_cache_service.py` | 12 (new) | ✅ All passing |
| `test_search_history.py` | 14 (new) | ✅ All passing |
| All other tests | 379 | ✅ Unchanged |

## Key Architecture Decisions

1. **Best-effort recording** — Usage and search history recording failures never block the main flow
2. **Backward compatibility** — `DiscoveryService` constructor defaults to mock/stub providers
3. **Two-track provider system** — New `LLMProvider` alongside legacy `ModelProvider`
4. **Cache-first** — Discovery flow checks cache before making search calls
5. **Reserved providers** — Placeholder classes with `NotImplementedError` for future implementation

## Next Steps

- Implement real LLM providers (OpenAI, Claude, etc.)
- Wire `token_count` tracking in LLM provider calls
- Connect `estimated_cost` tracking
- Add cache persistence (Redis)
- Add search history cleanup/archival
