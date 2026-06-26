# Search Cache Report

## Summary

| Item | Value |
|---|---|
| **Phase** | IV |
| **Status** | ✅ Complete |
| **Service** | `SearchCacheService` (`app/services/search_cache_service.py`) |
| **Type** | In-memory TTL-based cache |
| **Used By** | `DiscoveryService._run_discovery()` |

## Architecture

```
┌─────────────────────┐
│  DiscoveryService   │
│  _run_discovery()   │
│                     │
│  1. cache.get()     │ ← Check before searching
│     ┌──────────┐    │
│     │  CACHE   │    │
│     │  (dict)  │    │
│     └──────────┘    │
│  2. provider.search │ ← Only if cache miss
│  3. cache.set()     │ ← Store for next time
│  4. return results  │
└─────────────────────┘
```

## Configuration

```python
from app.providers.config import get_cache_config

config = get_cache_config()
# Returns: {"enabled": True, "ttl_seconds": 300}
```

## API

### get(query, *, language, brand, topic) → list | None
Returns cached results or `None` if:
- Cache is disabled
- Key doesn't exist
- Entry has expired

### set(query, results, *, language, brand, topic) → None
Stores results with current timestamp.

### invalidate(query=None, *, language, brand, topic) → None
Removes specific key or clears entire cache.

### clear() → None
Clears all entries and resets statistics.

## Key Features

| Feature | Description |
|---|---|
| **TTL** | Configurable expiry (default: 300 seconds) |
| **Disable** | Can be disabled via config or constructor |
| **Key composition** | `{query}|{language}|b:{brand}|t:{topic}` |
| **Case-insensitive** | Keys are lowercased |
| **Thread-safe** | Synchronous only (no asyncio lock needed for single-threaded) |
| **Statistics** | Hit/miss counters and size tracking |

## Test Coverage

| Test | Status |
|---|---|
| Cache miss on empty | ✅ |
| Cache hit after set | ✅ |
| Cache miss when disabled | ✅ |
| Set does nothing when disabled | ✅ |
| TTL expiry | ✅ |
| Case-insensitive keys | ✅ |
| Brand/topic differentiation | ✅ |
| Invalidate specific key | ✅ |
| Invalidate all | ✅ |
| Clear resets stats | ✅ |
| Stats tracking | ✅ |
| Enabled property | ✅ |
