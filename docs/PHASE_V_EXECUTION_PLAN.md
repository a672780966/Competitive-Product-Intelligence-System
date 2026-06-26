# CPIS Phase V — Collector Runtime Execution Plan

**Date:** 2026-06-26  
**Status:** Plan Document  
**Scope:** Registry-backed collector runtime selection, gated future collectors, retry/reporting telemetry, usage updates, task-detail UI exposure, and regression coverage.

---

## Objectives

Phase V upgrades collection from the legacy `CollectorSelector` path to a registry-driven runtime layer. The implementation must keep `direct_http` as the only default-enabled runtime, preserve graceful behavior when optional dependencies are absent, block prohibited sources before runtime execution, and expose execution details to backend APIs and the frontend.

## Sequential Execution Steps

### 1. Baseline and test quarantine confirmation

**Files to inspect/modify:** `backend/tests/test_collectors.py`, `backend/tests/test_collector_runtime.py`, `backend/pytest.ini` or equivalent test config if present

**Action:** Capture the current failure mode for `backend/tests/test_collectors.py`, especially the Playwright import error. Decide whether to replace the old test file in place or split legacy expectations into new registry-focused tests. Do not start functional edits until the baseline command and expected failure are documented in the Phase V evidence notes.

### 2. Add collector feature flags to runtime settings

**Files to modify:** `backend/app/core/__init__.py`, `.env.example` if present, `README.md` only if it already documents collection settings

**Action:** Add boolean settings for `COLLECTOR_PLAYWRIGHT_ENABLED`, `COLLECTOR_SCRAPLING_ENABLED`, `COLLECTOR_CRAWL4AI_ENABLED`, `COLLECTOR_RSS_ENABLED`, `COLLECTOR_PDF_ENABLED`, and `COLLECTOR_API_ENABLED`, all defaulting to `false`. Keep existing `COLLECTION_TIMEOUT_SECONDS`, `COLLECTION_MAX_RETRIES`, and `COLLECTION_USER_AGENT` unchanged. Implement parsing in the same style as existing settings and ensure unset environment variables disable optional collectors.

### 3. Define collector runtime metadata contract

**Files to modify:** `backend/app/collectors/registry.py`, `backend/app/collectors/base.py`, `backend/app/models/enums.py` if collector enum values need normalization

**Action:** Extend the registry entry shape to include runtime key, display name, provider factory or import path, enabled flag name, dependency state, supported `source_type` values, supported risk levels, default retry count, and disabled reason. Keep `BaseCollectorProvider` as the execution interface and avoid coupling registry metadata to legacy `HttpxCollector`/`PlaywrightCollector`.

### 4. Register default and placeholder collector runtimes

**Files to modify:** `backend/app/collectors/registry.py`, `backend/app/collectors/__init__.py`

**Action:** Register `direct_http` and `playwright` plus disabled placeholder entries for `scrapling`, `crawl4ai`, `rss`, `pdf`, and `api`. Placeholder entries must be feature-gated, disabled by default, and safe to list even when optional packages are not installed. Missing dependencies should produce a disabled reason instead of raising at import time.

### 5. Add placeholder provider modules

**Files to add/modify:** `backend/app/collectors/scrapling_runtime.py`, `backend/app/collectors/crawl4ai_runtime.py`, `backend/app/collectors/rss_runtime.py`, `backend/app/collectors/pdf_runtime.py`, `backend/app/collectors/api_runtime.py`

**Action:** Add minimal `BaseCollectorProvider`-compatible classes or factory functions for reserved runtimes. Each should fail gracefully with a clear unavailable error if invoked while disabled or missing dependencies. Keep implementation intentionally thin; Phase V reserves the runtime slots but does not implement full scraping engines.

### 6. Refactor `CollectorSelector` onto the registry

**Files to modify:** `backend/app/collectors/selector.py`, `backend/app/collectors/domain_lock.py`, `backend/app/models/source_candidate.py`, `backend/app/models/enums.py`

**Action:** Replace legacy selection logic that instantiates `HttpxCollector`/`PlaywrightCollector` with registry lookup and metadata filtering. Selection must respect feature flags, candidate `source_type`, `risk_level`, blocked-domain rules, and any existing `RecommendedCollector` values. For blocked sources, return a blocked selection result without creating an executable provider.

### 7. Add blocked-source selection contract

**Files to modify:** `backend/app/collectors/selector.py`, `backend/app/schemas/run_plan.py`, `backend/app/services/url_validator.py` if blocking is duplicated there

**Action:** Formalize the blocked-source behavior as a first-class selector outcome with `collector_runtime="blocked"`, status/reason fields, and retry count `0`. Ensure blocked sources cannot be accidentally routed to `direct_http` through fallback behavior.

### 8. Implement configurable `RetryPolicy`

**Files to add/modify:** `backend/app/collectors/retry_policy.py`, `backend/app/core/__init__.py`, `backend/app/tasks/collection.py`

**Action:** Add a `RetryPolicy` helper that returns per-runtime retry limits: `direct_http=3`, `playwright=1`, `scrapling=2`, `crawl4ai=1`, and `blocked=0`. Keep the policy configurable through settings or an override map while preserving these defaults. The task layer must consult the runtime-specific policy rather than only `COLLECTION_MAX_RETRIES`.

### 9. Introduce `CollectorExecutionReport` schema/model

**Files to add/modify:** `backend/app/models/collector_execution_report.py`, `backend/app/models/__init__.py`, `backend/app/schemas/task.py`, Alembic migration location if the project uses migrations

**Action:** Add a persisted execution report with `collector_runtime`, `url`, `status`, `started_at`, `finished_at`, `duration_ms`, `content_size`, `retry_count`, `error_message`, `snapshot_id`, and `task_id`. Use foreign keys to `CollectionTask` and `SourceSnapshot` where available. If migrations are not currently present, document and follow the repo’s established metadata creation pattern.

### 10. Add execution-report repository/service helpers

**Files to add/modify:** `backend/app/repositories/task_repository.py`, `backend/app/services/task_service.py`, `backend/app/tasks/collection.py`

**Action:** Add helper methods to create and finalize `CollectorExecutionReport` records. The write path should be best-effort only where appropriate for telemetry, but task status and retry events must still be accurate if report persistence fails.

### 11. Wire registry selector into Celery collection execution

**Files to modify:** `backend/app/tasks/collection.py`, `backend/app/services/collection_runner_service.py`, `backend/app/services/task_service.py`

**Action:** Replace old `CollectorSelector` usage with the registry-backed selector. The flow should select runtime, create a started execution report, execute the provider, record snapshot metadata, finalize the report, and route blocked selections directly to failed/blocked task handling without network access.

### 12. Emit retry and collector task events

**Files to modify:** `backend/app/tasks/collection.py`, `backend/app/models/task_event.py`, `backend/app/repositories/task_repository.py`

**Action:** Write `TaskEvent` rows for collector selection, collector start, retry attempts, retry exhaustion, blocked-source decisions, success, and failure. Retry events must include runtime, attempt number, retry limit, and concise error reason. Preserve existing pipeline events so downstream cleaning and extraction traces remain intact.

### 13. Expand usage hook metrics

**Files to modify:** `backend/app/tasks/collection.py`, `backend/app/repositories/usage_repository.py`, `backend/app/services/usage_service.py`, `backend/app/models/usage_daily_stat.py`, `backend/app/schemas/usage.py`

**Action:** Update usage recording to increment `collected_page_count`, `success_count`, and `failure_count`, and to accumulate collector duration. Keep best-effort semantics. If the existing `usage_daily_stat` model lacks collector-duration storage, add a compatible field and expose it through the usage schema/API.

### 14. Expose execution reports through task APIs

**Files to modify:** `backend/app/api/tasks.py`, `backend/app/schemas/task.py`, `backend/app/repositories/task_repository.py`

**Action:** Include the latest or full list of collector execution reports in task detail responses. At minimum, expose `collector_runtime`, `status`, `duration_ms`, `content_size`, and `error_message`/`error_reason` so the frontend can render the required task-detail fields without extra calls.

### 15. Update frontend task detail display

**Files to modify:** `frontend/src/types/index.ts`, `frontend/src/api/client.ts` if typed response helpers exist, `frontend/src/features/tasks/TaskDetail.tsx`, optionally `frontend/src/features/tasks/TaskList.tsx`

**Action:** Add UI fields for collector runtime, status, duration, content size, and error reason. Keep layout consistent with the existing task detail page, use compact status formatting, and handle missing reports gracefully for pre-Phase V tasks.

### 16. Add Phase V test suite and run regression

**Files to add/modify:** `backend/tests/test_collectors.py`, `backend/tests/test_collector_runtime.py`, `backend/tests/test_collector_selector_v2.py`, `backend/tests/test_retry_policy.py`, `backend/tests/test_collector_execution_report.py`, `backend/tests/test_usage_collection_metrics.py`, `backend/tests/test_collection_templates.py`, frontend test files if present

**Action:** Add focused tests for `CollectorRegistry`, registry-backed `CollectorSelector`, feature flags, graceful missing dependencies, `RetryPolicy`, `CollectorExecutionReport`, usage hook metrics, RunPlan whitelist behavior, and blocked-source handling. Then run the full backend regression from `backend/` and document the result. The target exit condition is no `test_collectors.py` collection error and a clean pytest run, or a clearly documented unrelated pre-existing failure with the Phase V tests passing.

## Acceptance Criteria

- `direct_http` remains the only default-enabled collector runtime.
- `playwright`, `scrapling`, `crawl4ai`, `rss`, `pdf`, and `api` are feature-gated and disabled by default.
- Missing optional collector dependencies do not break imports, registry listing, API startup, or pytest collection.
- Blocked sources resolve to `collector_runtime="blocked"` and never perform network collection.
- Celery collection uses the registry-backed selector, not the old direct legacy collector instantiation path.
- Retry limits are runtime-specific and retry attempts write `TaskEvent` records.
- Every collection attempt can produce a `CollectorExecutionReport` with runtime, timing, size, retry, error, snapshot, and task linkage.
- Usage metrics include collected pages, success/failure counts, and collector duration.
- Task detail API and UI show collector runtime, status, duration, content size, and error reason.
- Phase V tests cover registry, selector v2, feature flags, retry policy, execution reports, usage hook, RunPlan whitelist, and blocked sources.

## Verification Commands

Run from `backend/`:

```bash
pytest tests/test_collector_runtime.py tests/test_collector_selector_v2.py tests/test_retry_policy.py tests/test_collector_execution_report.py tests/test_usage_collection_metrics.py -q
pytest -q
```

Run from `frontend/` if package scripts are available:

```bash
npm run lint
npm run build
```

