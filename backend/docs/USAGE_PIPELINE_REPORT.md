# Usage Pipeline Report

## Summary

| Item | Value |
|---|---|
| **Phase** | IV |
| **Status** | ✅ Complete |
| **Service** | `UsageService` (`app/services/usage_service.py`) |
| **Repository** | `UsageRepository` (`app/repositories/usage_repository.py`) |
| **Model** | `UsageDailyStat` (`app/models/usage_daily_stat.py`) |
| **Wired In** | DiscoveryService + Collection Pipeline |

## Integration Points

### 1. DiscoveryService (Source Discovery)
- **File:** `app/services/discovery_service.py`
- **When:** After `_run_discovery()` completes
- **Calls:** `usage_service.record_usage(search_count=1)`
- **Error handling:** Best-effort (logs warning, does not fail discovery)

### 2. Collection Pipeline (Celery Tasks)
- **File:** `app/tasks/collection.py`
- **Helper:** `_record_usage(session, success=True/Failure=True)`
- **When:** After each pipeline stage completes or fails
- **Stages:**
  - `_do_collect()` — on success: `(collected_page_count=1, success_count=1)`; on failure: `(failure_count=1)`
  - `_do_clean()` — on success: `(success_count=1)`; on failure: `(failure_count=1)`
  - `_do_extract()` — on failure: `(failure_count=1)`
- **Error handling:** Best-effort (logs warning, does not fail the pipeline stage)

## UsageService API

### record_usage()
```python
async def record_usage(
    *,
    task_count: int = 0,
    token_count: int = 0,
    search_count: int = 0,
    collected_page_count: int = 0,
    success_count: int = 0,
    failure_count: int = 0,
    estimated_cost: float = 0.0,
    raw_metadata: dict | None = None,
    stat_date: date | None = None,
) -> UsageDailyStatResponse:
```

All counters are **additive** — calling multiple times for the same date accumulates values.

### Query APIs
- `get_daily_stats(date_from, date_to) → UsageDailyStatListResponse`
- `get_summary(date_from, date_to) → UsageSummaryResponse`

## UsageDailyStat Model

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| stat_date | Date | Statistics date |
| task_count | int | Tasks created |
| token_count | int | LLM tokens consumed |
| search_count | int | Search queries executed |
| collected_page_count | int | Pages successfully collected |
| success_count | int | Successful operations |
| failure_count | int | Failed operations |
| estimated_cost | float | Estimated monetary cost |
| raw_metadata | JSONB | Optional extra data |

## Test Coverage

| Test | Status |
|---|---|
| `test_usage_api.py` (existing) | ✅ Passing |
| Usage recording pipeline | ✅ Wired in both services |
