# Collector Execution Report

## Model
`backend/app/models/collector_execution_report.py`
- Table: `collector_execution_reports`
- Fields: `id`, `task_id` (FK), `snapshot_id` (FK, nullable), `collector_runtime`, `url`, `status`, `started_at`, `finished_at`, `duration_ms`, `content_size`, `retry_count`, `error_message`

## Schema
`backend/app/schemas/collector_execution_report.py`
- `CollectorExecutionReportResponse` — Pydantic model with `from_attributes=True`
- `CollectorExecutionReportListResponse` — paginated list

## API Endpoint
`GET /api/v1/collection-tasks/{task_id}/execution-reports`
Returns `list[CollectorExecutionReportResponse]`

## Example Report (success)
```json
{
  "id": "uuid...",
  "task_id": "uuid...",
  "snapshot_id": "uuid...",
  "collector_runtime": "direct_http",
  "url": "https://example.com/product",
  "status": "success",
  "started_at": "2026-06-26T12:00:00Z",
  "finished_at": "2026-06-26T12:00:01Z",
  "duration_ms": 1041,
  "content_size": 9279,
  "retry_count": 0,
  "error_message": null
}
```

## Example Report (blocked)
```json
{
  "id": "uuid...",
  "task_id": "uuid...",
  "collector_runtime": "blocked",
  "url": "https://blocked-site.com",
  "status": "blocked",
  "duration_ms": 0,
  "content_size": 0,
  "retry_count": 0,
  "error_message": "Source risk level is 'blocked'"
}
```
