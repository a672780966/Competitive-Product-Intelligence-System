# Phase V — Final Evidence Report

## Overview
Phase V upgrades CPIS collection from legacy `HttpxCollector`/`PlaywrightCollector` to a registry-driven runtime layer with feature flags, retry policy, execution reports, usage metrics, and frontend display.

## Tests
- **Phase V specific**: 34/34 passed
- **Pipeline tests**: 22/22 passed
- **Full regression** (excluding pre-existing cleaners failures): **521 passed**, 0 new failures
- **Pre-existing failures**: 15 in test_cleaners.py (missing lxml dependency, unrelated)
- **Frontend build**: ✅ `npm run build` passes

## Files Modified/Created

### New Files (6)
| File | Purpose |
|------|---------|
| `app/collectors/scrapling_runtime.py` | Scrapling placeholder provider |
| `app/collectors/crawl4ai_runtime.py` | Crawl4AI placeholder provider |
| `app/collectors/rss_runtime.py` | RSS placeholder provider |
| `app/collectors/pdf_runtime.py` | PDF placeholder provider |
| `app/collectors/api_runtime.py` | API placeholder provider |
| `app/collectors/retry_policy.py` | Per-kind retry limit configuration |
| `app/models/collector_execution_report.py` | Execution report DB model |
| `app/schemas/collector_execution_report.py` | Execution report API schema |
| `tests/test_phase_v.py` | 34 comprehensive Phase V tests |

### Modified Files (10+)
| File | Changes |
|------|---------|
| `app/core/__init__.py` | Added 6 feature flag settings |
| `app/collectors/registry.py` | CollectorMetadata, is_enabled(), get_metadata(), placeholder registration |
| `app/collectors/selector.py` | Refactored to use registry, SelectResult, blocked source handling |
| `app/tasks/collection.py` | Registry-backed fetch, execution reports, retry events, usage hooks |
| `app/api/tasks.py` | GET /execution-reports endpoint |
| `app/models/__init__.py` | Export CollectorExecutionReport |
| `app/repositories/task_repository.py` | get_execution_reports() method |
| `app/schemas/task.py` | Pydantic updates |
| `app/services/task_service.py` | Service layer updates |
| `frontend/src/features/tasks/TaskDetail.tsx` | Collector runtime display |

## Phase V Checklist

| Requirement | Status |
|-------------|--------|
| CollectorRegistry with placeholders (scrapling, crawl4ai, rss, pdf, api) | ✅ |
| CollectorSelector using registry, respect feature flags | ✅ |
| Blocked source → blocked kind, no network | ✅ |
| RetryPolicy: direct_http=3, playwright=1, scrapling=2, crawl4ai=1, blocked=0 | ✅ |
| Retry writes TaskEvent | ✅ |
| CollectorExecutionReport model + API | ✅ |
| Execution reports in task detail API | ✅ |
| Usage hook: collected_page_count, success_count, failure_count | ✅ |
| Frontend: collector_runtime, status, duration, content_size, error_reason | ✅ |
| Tests: registry, selector v2, retry policy, execution report, usage, blocked | ✅ |
| No real Scrapling/Crawl4AI pipeline | ✅ |
| No enabling Playwright by default | ✅ |
| No push/tag/merge/deploy | ✅ |
| No .env changes | ✅ |
