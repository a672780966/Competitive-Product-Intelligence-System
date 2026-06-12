"""CPIS V1 — Task schemas for API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TaskPriority, TaskStatus


# ── Request schemas ─────────────────────────────────────────────


class CreateTaskRequest(BaseModel):
    """Request body for creating a single collection task."""

    source_url: str = Field(..., max_length=2048, min_length=1, description="The URL to collect")
    category_hint: str | None = Field(None, max_length=64)
    language_hint: str | None = Field(None, max_length=16)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    auto_sync_feishu: bool = Field(default=False)
    created_by: str | None = Field(None, max_length=128)


class BatchCreateTaskRequest(BaseModel):
    """Request body for batch-creating collection tasks."""

    tasks: list[CreateTaskRequest] = Field(..., min_length=1, max_length=100)


class TaskListQuery(BaseModel):
    """Query parameters for listing tasks."""

    status: TaskStatus | None = None
    domain: str | None = None
    keyword: str | None = Field(None, description="Search in source_url")
    priority: TaskPriority | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── Response schemas ────────────────────────────────────────────


class TaskEventResponse(BaseModel):
    """Single task event for API response."""

    id: uuid.UUID
    stage: str
    status: str
    message: str | None
    duration_ms: int | None
    error_code: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Collection task detail for API response."""

    id: uuid.UUID
    source_url: str
    normalized_url: str | None = None
    domain: str | None = None
    status: str
    priority: int
    category_hint: str | None = None
    language_hint: str | None = None
    auto_sync_feishu: bool
    retry_count: int
    max_retries: int
    error_code: str | None = None
    error_message: str | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailResponse(TaskResponse):
    """Task detail including event history."""

    events: list[TaskEventResponse] = []


class PaginatedTaskResponse(BaseModel):
    """Paginated list of tasks."""

    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchCreateTaskResponse(BaseModel):
    """Response for batch creation."""

    created: int
    tasks: list[TaskResponse]
    errors: list[dict] = Field(default_factory=list)
