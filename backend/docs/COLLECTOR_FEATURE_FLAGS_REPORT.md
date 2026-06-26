# Feature Flags Report

## Settings Added (backend/app/core/__init__.py)
| Setting | Default | Description |
|---------|---------|-------------|
| `COLLECTOR_PLAYWRIGHT_ENABLED` | `False` | Enable Playwright JS rendering |
| `COLLECTOR_SCRAPLING_ENABLED` | `False` | Enable Scrapling collector |
| `COLLECTOR_CRAWL4AI_ENABLED` | `False` | Enable Crawl4AI collector |
| `COLLECTOR_RSS_ENABLED` | `False` | Enable RSS feed collector |
| `COLLECTOR_PDF_ENABLED` | `False` | Enable PDF download collector |
| `COLLECTOR_API_ENABLED` | `False` | Enable API data collector |

## Graceful Degradation
- Missing dependencies never break imports
- Placeholder providers raise `NotImplementedError` with clear message
- `CollectorRuntimeRegistry.is_enabled()` checks both flag and deps
- `get_metadata()` includes disabled_reason string

## Default State
Only `direct_http` is production-ready and always enabled.
All optional collectors require explicit opt-in via env vars.
