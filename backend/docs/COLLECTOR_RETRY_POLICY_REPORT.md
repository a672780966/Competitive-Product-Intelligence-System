# Retry Policy Report

## Implementation
- `backend/app/collectors/retry_policy.py`
- `RetryPolicy(overrides=None)` class

## Default Per-Kind Retry Limits
| Kind | Max Retries |
|------|------------|
| direct_http | 3 |
| playwright | 1 |
| scrapling | 2 |
| crawl4ai | 1 |
| rss | 3 |
| pdf | 2 |
| api | 3 |
| blocked | 0 |

## Fallback Chain
1. Explicit override (constructor)
2. Default for the kind
3. Global `COLLECTION_MAX_RETRIES` setting
4. 1 (ultimate fallback)

## TaskEvent Integration
- `_do_collect()` writes TaskEvent for collector selection, start, failure
- Retry events include runtime and attempt information
- Blocked-source decisions recorded as distinct events
