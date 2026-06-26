# Phase V — Collector Runtime Architecture

## Overview

Phase V upgrades CPIS collection from the legacy `CollectorSelector` (direct `HttpxCollector`/`PlaywrightCollector` instantiation) to a registry-driven runtime layer.

## Architecture

```
CollectorRuntimeRegistry (singleton)
├── direct_http (enabled, always available)
├── playwright (feature-gated, COLLECTOR_PLAYWRIGHT_ENABLED)
├── scrapling (placeholder, feature-gated)
├── crawl4ai (placeholder, feature-gated)
├── rss (placeholder, feature-gated)
├── pdf (placeholder, feature-gated)
├── api (placeholder, feature-gated)
└── blocked (always available, no network)

CollectorSelector
├── select(url, source_type, risk_level) → SelectResult
│   ├── blocked → collector_kind="blocked", runtime=None
│   └── normal → collector_kind, runtime, reason
└── fetch(url) — legacy compat wrapper

CollectorExecutionReport (DB model)
├── task_id → CollectionTask
├── snapshot_id → SourceSnapshot
├── collector_runtime, url, status
├── started_at, finished_at, duration_ms
├── content_size, retry_count, error_message
└── created_at, updated_at

RetryPolicy
├── direct_http=3, playwright=1, scrapling=2
├── crawl4ai=1, blocked=0, rss=3, pdf=2, api=3
└── overrides via constructor
```

## Feature Flags (all default false)
- `COLLECTOR_PLAYWRIGHT_ENABLED`
- `COLLECTOR_SCRAPLING_ENABLED`
- `COLLECTOR_CRAWL4AI_ENABLED`
- `COLLECTOR_RSS_ENABLED`
- `COLLECTOR_PDF_ENABLED`
- `COLLECTOR_API_ENABLED`

## Data Flow in Celery Tasks
1. `_do_collect()` creates `CollectorSelector`
2. Calls `selector.select(url)` → gets `SelectResult`
3. If `collector_kind == "blocked"` → status=BLOCKED, skip fetch
4. Creates `CollectorExecutionReport(status="started")`
5. Calls `sel.runtime.fetch(url, timeout=20)`
6. Updates report with success/failure, duration, size, errors
7. Keeps existing usage recording + TaskEvent creation
8. Chains to `clean_content.delay()` on success
