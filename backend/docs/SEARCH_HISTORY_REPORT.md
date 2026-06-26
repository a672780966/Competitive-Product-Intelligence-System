# Search History Report

## Summary

| Item | Value |
|---|---|
| **Phase** | IV |
| **Status** | ✅ Complete |
| **Model** | `SearchHistory` (`app/models/search_history.py`) |
| **Repository** | `SearchHistoryRepository` (`app/repositories/search_history_repository.py`) |
| **Migration** | `004_add_search_history.py` |

## Model

```sql
CREATE TABLE search_history (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query         VARCHAR(1024) NOT NULL,
    provider      VARCHAR(64) NOT NULL,
    result_count  INTEGER NOT NULL DEFAULT 0,
    language      VARCHAR(16),
    brand         VARCHAR(255),
    topic         VARCHAR(255),
    session_id    UUID REFERENCES discovery_sessions(id) ON DELETE SET NULL,
    raw_metadata  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_history_query ON search_history(query);
CREATE INDEX idx_search_history_session ON search_history(session_id);
```

## Repository API

### record(query, provider, result_count, *, brand, topic, session_id, raw_metadata) → SearchHistory
Records a search query with metadata. Generates UUID automatically.

### list_history(*, limit=50, offset=0) → list[SearchHistory]
Lists recent search history entries, newest first. Supports pagination.

### get_by_session(session_id) → SearchHistory | None
Gets the search history record for a specific discovery session.

### count_by_query(query, *, provider) → int
Counts how many times a query has been searched (optionally filtered by provider).

## Integration

Called from `DiscoveryService._run_discovery()` after successful search:

```python
await self._search_history_repo.record(
    query=query,
    provider=provider_name,
    result_count=len(raw_results),
    brand=brand,
    topic=topic,
    session_id=session.id,
    raw_metadata={"candidates_created": len(ranked_candidates)},
)
```

Uses **best-effort** error handling — failures to record history are logged but never block the discovery flow.

## Test Coverage

| Test | Status |
|---|---|
| Model instantiation (basic fields) | ✅ |
| Model with all fields | ✅ |
| Model defaults | ✅ |
| Model __repr__ | ✅ |
| Repository record() | ✅ |
| Record with optional fields | ✅ |
| List history (all records) | ✅ |
| List history respects limit | ✅ |
| List history respects offset | ✅ |
| Get by session (found) | ✅ |
| Get by session (not found) | ✅ |
| Count by query | ✅ |
| Count by query with provider filter | ✅ |
