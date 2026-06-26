"""Pydantic schemas for Usage API — daily stats and summary."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Request Schemas ─────────────────────────────────────────────

class DailyUsageQueryParams(BaseModel):
    """Query parameters for GET /api/v1/usage/daily."""

    date_from: date | None = Field(None, description="Start date (inclusive)")
    date_to: date | None = Field(None, description="End date (inclusive)")


# ── Response Schemas ────────────────────────────────────────────

class UsageDailyStatResponse(BaseModel):
    """Single day's usage statistics."""

    id: uuid.UUID
    stat_date: date
    task_count: int
    token_count: int
    search_count: int
    collected_page_count: int
    success_count: int
    failure_count: int
    estimated_cost: float
    raw_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UsageDailyStatListResponse(BaseModel):
    """Paginated list of daily usage stats."""

    items: list[UsageDailyStatResponse]
    total: int
    date_from: date | None = None
    date_to: date | None = None


class UsageSummaryResponse(BaseModel):
    """Aggregated usage summary."""

    total_task_count: int
    total_token_count: int
    total_search_count: int
    total_collected_page_count: int
    total_success_count: int
    total_failure_count: int
    total_estimated_cost: float
    total_days: int
