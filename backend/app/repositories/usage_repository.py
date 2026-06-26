"""Repository for UsageDailyStat model — daily aggregated usage statistics."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsageDailyStat


class UsageRepository:
    """Data access for UsageDailyStat."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Upsert ───────────────────────────────────────────────────

    async def upsert_daily_stat(
        self,
        stat_date: date,
        *,
        task_count: int = 0,
        token_count: int = 0,
        search_count: int = 0,
        collected_page_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        estimated_cost: float = 0.0,
        raw_metadata: dict | None = None,
    ) -> UsageDailyStat:
        """Atomically increment counters for a given date.

        If no record exists for that date, a new one is created with the
        provided values. If a record already exists, the counters are
        *added* to the existing values (cumulative).
        """
        existing = await self.get_by_date(stat_date)
        if existing is not None:
            existing.task_count += task_count
            existing.token_count += token_count
            existing.search_count += search_count
            existing.collected_page_count += collected_page_count
            existing.success_count += success_count
            existing.failure_count += failure_count
            existing.estimated_cost += estimated_cost
            if raw_metadata is not None:
                existing.raw_metadata = raw_metadata
            await self._db.flush()
            # Refresh to eagerly load server-side defaults (e.g. updated_at)
            await self._db.refresh(existing)
            return existing

        stat = UsageDailyStat(
            stat_date=stat_date,
            task_count=task_count,
            token_count=token_count,
            search_count=search_count,
            collected_page_count=collected_page_count,
            success_count=success_count,
            failure_count=failure_count,
            estimated_cost=estimated_cost,
            raw_metadata=raw_metadata,
        )
        self._db.add(stat)
        await self._db.flush()
        return stat

    # ── Query ────────────────────────────────────────────────────

    async def get_by_date(self, stat_date: date) -> UsageDailyStat | None:
        """Get a single day's stats by date."""
        result = await self._db.execute(
            select(UsageDailyStat).where(
                UsageDailyStat.stat_date == stat_date,
            ),
        )
        return result.scalar_one_or_none()

    async def get_daily_stats(
        self,
        date_from: date,
        date_to: date,
    ) -> list[UsageDailyStat]:
        """Get daily stats within a date range (inclusive), ordered by date."""
        result = await self._db.execute(
            select(UsageDailyStat)
            .where(
                UsageDailyStat.stat_date >= date_from,
                UsageDailyStat.stat_date <= date_to,
            )
            .order_by(UsageDailyStat.stat_date.asc()),
        )
        return list(result.scalars().all())

    async def get_summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Get aggregated totals across all (or filtered) daily records.

        Returns a dict with total_task_count, total_token_count,
        total_search_count, total_collected_page_count,
        total_success_count, total_failure_count, total_estimated_cost,
        and total_days.
        """
        query = select(
            func.coalesce(func.sum(UsageDailyStat.task_count), 0).label("total_task_count"),
            func.coalesce(func.sum(UsageDailyStat.token_count), 0).label("total_token_count"),
            func.coalesce(func.sum(UsageDailyStat.search_count), 0).label("total_search_count"),
            func.coalesce(func.sum(UsageDailyStat.collected_page_count), 0).label("total_collected_page_count"),
            func.coalesce(func.sum(UsageDailyStat.success_count), 0).label("total_success_count"),
            func.coalesce(func.sum(UsageDailyStat.failure_count), 0).label("total_failure_count"),
            func.coalesce(func.sum(UsageDailyStat.estimated_cost), 0.0).label("total_estimated_cost"),
            func.count(UsageDailyStat.id).label("total_days"),
        )
        if date_from is not None:
            query = query.where(UsageDailyStat.stat_date >= date_from)
        if date_to is not None:
            query = query.where(UsageDailyStat.stat_date <= date_to)

        result = await self._db.execute(query)
        row = result.one()
        return {
            "total_task_count": row.total_task_count or 0,
            "total_token_count": row.total_token_count or 0,
            "total_search_count": row.total_search_count or 0,
            "total_collected_page_count": row.total_collected_page_count or 0,
            "total_success_count": row.total_success_count or 0,
            "total_failure_count": row.total_failure_count or 0,
            "total_estimated_cost": float(row.total_estimated_cost or 0.0),
            "total_days": row.total_days or 0,
        }
