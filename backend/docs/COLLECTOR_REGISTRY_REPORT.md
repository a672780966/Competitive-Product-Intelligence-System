# Collector Registry Report

## Implementation
- `backend/app/collectors/registry.py` — `CollectorRuntimeRegistry` with:
  - `CollectorMetadata` dataclass (kind, display_name, description, enabled, deps, retry_count, source_types, risk_levels)
  - `is_enabled(kind)` — checks feature flag + dependencies
  - `get_metadata(kind)` — runtime metadata with disabled_reason
  - `get_supported_kinds()` — all registered kinds (providers + feature-gated + metadata-only)
  - `execute(kind, url)` — run collector by kind string

## Registered Collectors
| Kind | Enabled | Default Retry | Dependencies |
|------|---------|--------------|--------------|
| direct_http | ✅ | 3 | none |
| playwright | ❌ (feature flag) | 1 | playwright |
| scrapling | ❌ (placeholder) | 2 | none (minimal module) |
| crawl4ai | ❌ (placeholder) | 1 | none (minimal module) |
| rss | ❌ (placeholder) | 3 | none (minimal module) |
| pdf | ❌ (placeholder) | 2 | none (minimal module) |
| api | ❌ (placeholder) | 3 | none (minimal module) |
| blocked | ✅ | 0 | none |

## Placeholder Providers
5 minimal modules created at `backend/app/collectors/{kind}_runtime.py`. Each raises `NotImplementedError` with clear "not enabled" message if invoked while disabled.

## Verification
```python
r = get_collector_registry()
r.get_supported_kinds()  # ['direct_http', 'playwright', 'scrapling', ...]
r.is_enabled('direct_http')  # True
r.is_enabled('scrapling')    # False
```
