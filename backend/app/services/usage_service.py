"""UsageService — recording and querying daily usage statistics.

This service provides the core business logic for the Usage API.
It delegates data access to UsageRepository and returns Pydantic
response schemas.

Integration notes (for later nodes):
- DiscoveryService should call record_usage(search_count=1) after search
- Collection runner should call record_usage(task_count=1, token_count=N)
  when a collection task completes
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import UsageDailyStat
from app.repositories.usage_repository import UsageRepository
from app.schemas.usage import (
    UsageDailyStatListResponse,
    UsageDailyStatResponse,
    UsageSummaryResponse,
)

logger = get_logger(__name__)


class UsageService:
    """Business logic for usage statistics."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = UsageRepository(db)

    # ── Recording ────────────────────────────────────────────────

    async def record_usage(
        self,
        *,
        task_count: int = 0,
        token_count: int = 0,
        search_count: int = 0,
        collected_page_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        estimated_cost: float = 0.0,
        raw_metadata: dict | None = None,
        stat_date: date | None = None,
    ) -> UsageDailyStatResponse:
        """Record usage statistics for a given date (default: today).

        All counters are additive — calling this multiple times for the
        same date accumulates the values.
        """
        if stat_date is None:
            stat_date = date.today()

        stat = await self._repo.upsert_daily_stat(
            stat_date,
            task_count=task_count,
            token_count=token_count,
            search_count=search_count,
            collected_page_count=collected_page_count,
            success_count=success_count,
            failure_count=failure_count,
            estimated_cost=estimated_cost,
            raw_metadata=raw_metadata,
        )

        logger.debug(
            "usage_recorded",
            stat_date=str(stat_date),
            task_count=task_count,
            token_count=token_count,
            search_count=search_count,
        )

        return self._stat_to_response(stat)

    # ── Querying ─────────────────────────────────────────────────

    async def get_daily_stats(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> UsageDailyStatListResponse:
        """Get daily usage stats within a date range.

        Defaults to the last 30 days if neither date_from nor date_to
        is provided.
        """
        today = date.today()
        if date_from is None and date_to is None:
            date_from = today - timedelta(days=30)
            date_to = today
        elif date_from is None and date_to is not None:
            date_from = date_to - timedelta(days=30)
        elif date_to is None and date_from is not None:
            date_to = date_from + timedelta(days=30)

        stats = await self._repo.get_daily_stats(date_from, date_to)

        return UsageDailyStatListResponse(
            items=[self._stat_to_response(s) for s in stats],
            total=len(stats),
            date_from=date_from,
            date_to=date_to,
        )

    async def get_summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> UsageSummaryResponse:
        """Get aggregated usage summary.

        Returns totals across all daily records, optionally filtered
        by date range.
        """
        summary = await self._repo.get_summary(
            date_from=date_from, date_to=date_to,
        )

        return UsageSummaryResponse(**summary)

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _stat_to_response(stat: UsageDailyStat) -> UsageDailyStatResponse:
        return UsageDailyStatResponse(
            id=stat.id,
            stat_date=stat.stat_date,
            task_count=stat.task_count,
            token_count=stat.token_count,
            search_count=stat.search_count,
            collected_page_count=stat.collected_page_count,
            success_count=stat.success_count,
            failure_count=stat.failure_count,
            estimated_cost=stat.estimated_cost,
            raw_metadata=stat.raw_metadata,
            created_at=stat.created_at,
            updated_at=stat.updated_at,
        )
