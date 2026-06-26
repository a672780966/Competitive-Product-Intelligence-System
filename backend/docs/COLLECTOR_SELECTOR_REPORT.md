# Collector Selector Report

## Implementation
- `backend/app/collectors/selector.py` — refactored `CollectorSelector`:
  - Uses `CollectorRuntimeRegistry` for registration + metadata
  - `select(url, source_type='other', risk_level='low')` → `SelectResult(collector_kind, runtime, reason)`
  - Blocked sources → `collector_kind="blocked"`, `runtime=None`, retry=0
  - Falls back to feature-gated collectors only when direct_http is disabled
  - `fetch(url)` — legacy compatibility wrapper

## Selection Rules
1. `risk_level == "blocked"` → immediately return blocked kind, no network
2. `direct_http` is the only default-enabled collector
3. Feature-gated collectors only active when feature flag is enabled
4. Fallback order: direct_http → feature-gated → none

## Blocked Source Handling
- Returns `SelectResult(collector_kind="blocked", runtime=None)`
- `_do_collect()` sets task status to `BLOCKED`
- `RetryPolicy.get_max_retries('blocked')` returns 0
- Writes `CollectorExecutionReport` with status="blocked"
- No network call ever made for blocked sources

## Verification
```python
selector = CollectorSelector(registry=get_collector_registry())
sel = selector.select("https://example.com")
assert sel.collector_kind == "direct_http"

sel = selector.select("https://evil.com", risk_level="blocked")
assert sel.collector_kind == "blocked"
assert sel.runtime is None
```
