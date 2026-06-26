"""CPIS V1 — CollectorExecutionReport schemas for API responses."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CollectorExecutionReportResponse(BaseModel):
    """Collector execution report detail for API response."""

    id: uuid.UUID
    task_id: uuid.UUID
    snapshot_id: uuid.UUID | None = None
    collector_runtime: str
    url: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    content_size: int | None = None
    retry_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectorExecutionReportListResponse(BaseModel):
    """Paginated list of execution reports."""

    items: list[CollectorExecutionReportResponse]
    total: int
    page: int = 1
    page_size: int = 20
