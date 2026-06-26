"""CPIS V1 — Usage API routes.

Endpoints:
  GET /api/v1/usage/daily     — Daily usage stats with optional date range filter
  GET /api/v1/usage/summary   — Aggregated usage summary

No billing or approval workflows are implemented here.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.usage import (
    UsageDailyStatListResponse,
    UsageSummaryResponse,
)
from app.services.usage_service import UsageService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get(
    "/daily",
    response_model=UsageDailyStatListResponse,
    summary="Daily usage statistics",
    description="Get daily usage stats within a date range. Defaults to last 30 days.",
)
async def get_daily_stats(
    date_from: date | None = Query(None, description="Start date (inclusive)"),
    date_to: date | None = Query(None, description="End date (inclusive)"),
    db: AsyncSession = Depends(get_db),
) -> UsageDailyStatListResponse:
    """Get daily usage statistics with optional date range filter."""
    service = UsageService(db)
    return await service.get_daily_stats(date_from=date_from, date_to=date_to)


@router.get(
    "/summary",
    response_model=UsageSummaryResponse,
    summary="Aggregated usage summary",
    description="Get overall totals for tasks, tokens, searches, pages, and cost.",
)
async def get_summary(
    date_from: date | None = Query(None, description="Start date (inclusive)"),
    date_to: date | None = Query(None, description="End date (inclusive)"),
    db: AsyncSession = Depends(get_db),
) -> UsageSummaryResponse:
    """Get aggregated usage summary (total tasks, tokens, searches, etc.)."""
    service = UsageService(db)
    return await service.get_summary(date_from=date_from, date_to=date_to)
