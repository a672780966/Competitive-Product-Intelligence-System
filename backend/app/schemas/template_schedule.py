"""Pydantic schemas for CollectionTemplate and ScheduledCollection APIs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CollectionTemplateStatus, ScheduleType


# ── CollectionTemplate Schemas ───────────────────────────────────


class TemplateUpdateRequest(BaseModel):
    """Request body for updating a collection template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: CollectionTemplateStatus | None = None


class TemplateResponse(BaseModel):
    """Response model for a collection template."""

    id: uuid.UUID
    name: str
    description: str | None = None
    target_brand: str | None = None
    topic: str | None = None
    source_plan: dict
    run_plan: dict
    feishu_sync_enabled: bool = False
    status: str
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    """Paginated list of collection templates."""

    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TemplateRunResponse(BaseModel):
    """Response from running a template."""

    template_id: uuid.UUID
    tasks_created: int
    message: str


# ── ScheduledCollection Schemas ──────────────────────────────────


class ScheduledCollectionCreateRequest(BaseModel):
    """Request body for creating a scheduled collection."""

    template_id: uuid.UUID
    schedule_type: ScheduleType = ScheduleType.DAILY
    cron_expr: str | None = Field(None, max_length=128)
    interval_minutes: int | None = Field(None, ge=1, le=44640)
    enabled: bool = True
    max_failures_before_pause: int = Field(default=3, ge=1, le=100)


class ScheduledCollectionUpdateRequest(BaseModel):
    """Request body for updating a scheduled collection."""

    schedule_type: ScheduleType | None = None
    cron_expr: str | None = None
    interval_minutes: int | None = None
    enabled: bool | None = None


class ScheduledCollectionResponse(BaseModel):
    """Response model for a scheduled collection."""

    id: uuid.UUID
    template_id: uuid.UUID
    schedule_type: str
    cron_expr: str | None = None
    interval_minutes: int | None = None
    enabled: bool = True
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_status: str | None = None
    failure_count: int = 0
    max_failures_before_pause: int = 3
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScheduledCollectionListResponse(BaseModel):
    """Paginated list of scheduled collections."""

    items: list[ScheduledCollectionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ScheduledCollectionDetailResponse(BaseModel):
    """Detailed response including template info."""

    schedule: ScheduledCollectionResponse
    template: TemplateResponse | None = None
