"""ScheduleManager — scheduled collection lifecycle management.

Handles:
- Creating/updating/listingscheduled collections
- Calculating next_run_at from cron/interval config
- Checking if a schedule is due and executing it
- Tracking failure counts and pausing on too many failures
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import CollectionTemplate, TaskEvent
from app.models.enums import ScheduleType
from app.models.scheduled_collection import ScheduledCollection
from app.schemas.template_schedule import (
    ScheduledCollectionCreateRequest,
    ScheduledCollectionDetailResponse,
    ScheduledCollectionListResponse,
    ScheduledCollectionResponse,
    ScheduledCollectionUpdateRequest,
    TemplateResponse,
)
from app.services.template_service import TemplateService

logger = get_logger(__name__)

_MAX_FAILURES_BEFORE_PAUSE_DEFAULT = 3


class ScheduleManager:
    """Business logic for scheduled collection management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._template_service = TemplateService(db)

    # ── CRUD ─────────────────────────────────────────────────────

    async def create_schedule(
        self,
        req: ScheduledCollectionCreateRequest,
    ) -> ScheduledCollectionResponse | None:
        """Create a new scheduled collection.

        Validates that the template exists and calculates next_run_at.
        """
        # Verify template exists
        template_result = await self._db.execute(
            select(CollectionTemplate).where(
                CollectionTemplate.id == req.template_id,
            ),
        )
        template = template_result.scalar_one_or_none()
        if template is None:
            return None

        next_run_at = self._calculate_next_run(
            req.schedule_type,
            cron_expr=req.cron_expr,
            interval_minutes=req.interval_minutes,
        )

        schedule = ScheduledCollection(
            template_id=req.template_id,
            schedule_type=req.schedule_type,
            cron_expr=req.cron_expr,
            interval_minutes=req.interval_minutes,
            enabled=req.enabled,
            next_run_at=next_run_at,
            max_failures_before_pause=req.max_failures_before_pause,
        )
        self._db.add(schedule)
        await self._db.flush()

        logger.info(
            "schedule_created",
            schedule_id=str(schedule.id),
            template_id=str(req.template_id),
            schedule_type=req.schedule_type.value if hasattr(req.schedule_type, "value") else req.schedule_type,
        )

        return self._to_response(schedule)

    async def list_schedules(
        self,
        *,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ScheduledCollectionListResponse:
        """List scheduled collections with pagination."""
        query = select(ScheduledCollection)
        count_query = select(func.count(ScheduledCollection.id))

        if enabled is not None:
            query = query.where(ScheduledCollection.enabled == enabled)
            count_query = count_query.where(ScheduledCollection.enabled == enabled)

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        query = (
            query
            .order_by(ScheduledCollection.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())

        total_pages = max(1, (total + page_size - 1) // page_size)

        return ScheduledCollectionListResponse(
            items=[self._to_response(s) for s in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_schedule(
        self, schedule_id: uuid.UUID,
    ) -> ScheduledCollectionResponse | None:
        """Get a scheduled collection by ID."""
        result = await self._db.execute(
            select(ScheduledCollection).where(
                ScheduledCollection.id == schedule_id,
            ),
        )
        schedule = result.scalar_one_or_none()
        if schedule is None:
            return None
        return self._to_response(schedule)

    async def get_schedule_detail(
        self, schedule_id: uuid.UUID,
    ) -> ScheduledCollectionDetailResponse | None:
        """Get a scheduled collection with its template info."""
        result = await self._db.execute(
            select(ScheduledCollection)
            .where(ScheduledCollection.id == schedule_id)
            .options(selectinload(ScheduledCollection.template)),
        )
        schedule = result.scalar_one_or_none()
        if schedule is None:
            return None

        template_resp = None
        if schedule.template:
            template_resp = TemplateResponse.model_validate(schedule.template)

        return ScheduledCollectionDetailResponse(
            schedule=self._to_response(schedule),
            template=template_resp,
        )

    async def update_schedule(
        self,
        schedule_id: uuid.UUID,
        req: ScheduledCollectionUpdateRequest,
    ) -> ScheduledCollectionResponse | None:
        """Update a scheduled collection's config."""
        values: dict[str, Any] = {}

        if req.schedule_type is not None:
            values["schedule_type"] = req.schedule_type.value if hasattr(req.schedule_type, "value") else req.schedule_type
        if req.cron_expr is not None:
            values["cron_expr"] = req.cron_expr
        if req.interval_minutes is not None:
            values["interval_minutes"] = req.interval_minutes
        if req.enabled is not None:
            values["enabled"] = req.enabled
            if req.enabled:
                # Recalculate next_run_at when enabling
                schedule = await self._get_schedule_orm(schedule_id)
                if schedule:
                    values["next_run_at"] = self._calculate_next_run(
                        schedule.schedule_type,
                        cron_expr=schedule.cron_expr,
                        interval_minutes=schedule.interval_minutes,
                    )

        if values:
            stmt = (
                update(ScheduledCollection)
                .where(ScheduledCollection.id == schedule_id)
                .values(**values)
            )
            await self._db.execute(stmt)

        return await self.get_schedule(schedule_id)

    # ── Execution ────────────────────────────────────────────────

    async def execute_due_schedules(self) -> list[dict]:
        """Check and execute all schedules that are due.

        Returns list of execution results.
        """
        now = datetime.now(timezone.utc)
        result = await self._db.execute(
            select(ScheduledCollection).where(
                ScheduledCollection.enabled == True,  # noqa: E712
                ScheduledCollection.next_run_at <= now,
            ).options(selectinload(ScheduledCollection.template)),
        )
        due_schedules = list(result.scalars().all())

        results: list[dict] = []
        for schedule in due_schedules:
            exec_result = await self.execute_schedule(schedule.id)
            results.append(exec_result)

        return results

    async def execute_schedule(
        self, schedule_id: uuid.UUID,
    ) -> dict:
        """Execute a single schedule immediately.

        Runs the associated template and updates last_run_at/next_run_at.
        Records TaskEvent for the scheduled run.
        """
        schedule = await self._get_schedule_orm(schedule_id)
        if schedule is None:
            return {"schedule_id": str(schedule_id), "status": "failed", "error": "Schedule not found"}

        if not schedule.enabled:
            return {"schedule_id": str(schedule_id), "status": "skipped", "error": "Schedule is disabled"}

        try:
            template_resp = await self._template_service.run_template(
                schedule.template_id,
                created_by="scheduler",
            )

            if template_resp is None:
                raise ValueError("Template not found or execution failed")

            # Update schedule state
            now = datetime.now(timezone.utc)
            next_run = self._calculate_next_run(
                schedule.schedule_type,
                cron_expr=schedule.cron_expr,
                interval_minutes=schedule.interval_minutes,
                from_time=now,
            )

            stmt = (
                update(ScheduledCollection)
                .where(ScheduledCollection.id == schedule_id)
                .values(
                    last_run_at=now,
                    next_run_at=next_run,
                    last_status="completed",
                    failure_count=0,
                )
            )
            await self._db.execute(stmt)

            logger.info(
                "schedule_executed",
                schedule_id=str(schedule_id),
                tasks_created=template_resp.tasks_created,
            )

            return {
                "schedule_id": str(schedule_id),
                "status": "completed",
                "tasks_created": template_resp.tasks_created,
            }

        except Exception as exc:
            logger.error(
                "schedule_execution_failed",
                schedule_id=str(schedule_id),
                error=str(exc),
            )

            # Increment failure count
            new_failure_count = (schedule.failure_count or 0) + 1
            max_failures = schedule.max_failures_before_pause or _MAX_FAILURES_BEFORE_PAUSE_DEFAULT

            values: dict[str, Any] = {
                "last_status": "failed",
                "failure_count": new_failure_count,
            }

            if new_failure_count >= max_failures:
                values["enabled"] = False
                logger.warning(
                    "schedule_paused_due_to_failures",
                    schedule_id=str(schedule_id),
                    failure_count=new_failure_count,
                    max_failures=max_failures,
                )

            stmt = (
                update(ScheduledCollection)
                .where(ScheduledCollection.id == schedule_id)
                .values(**values)
            )
            await self._db.execute(stmt)

            return {
                "schedule_id": str(schedule_id),
                "status": "failed",
                "error": str(exc),
                "failure_count": new_failure_count,
            }

    # ── Internal ─────────────────────────────────────────────────

    async def _get_schedule_orm(
        self, schedule_id: uuid.UUID,
    ) -> ScheduledCollection | None:
        """Get the ORM model for a schedule."""
        result = await self._db.execute(
            select(ScheduledCollection).where(
                ScheduledCollection.id == schedule_id,
            ),
        )
        return result.scalar_one_or_none()

    def _calculate_next_run(
        self,
        schedule_type: ScheduleType | str,
        *,
        cron_expr: str | None = None,
        interval_minutes: int | None = None,
        from_time: datetime | None = None,
    ) -> datetime | None:
        """Calculate the next run time based on schedule config.

        Uses croniter for cron expressions, timedelta for interval.
        """
        now = from_time or datetime.now(timezone.utc)

        stype = schedule_type.value if hasattr(schedule_type, "value") else schedule_type

        if stype in ("cron", ScheduleType.CRON.value if hasattr(ScheduleType.CRON, "value") else "cron"):
            if cron_expr:
                try:
                    cron = croniter(cron_expr, now)
                    return cron.get_next(datetime)
                except (ValueError, KeyError) as exc:
                    logger.error("cron_parse_error", expr=cron_expr, error=str(exc))
                    return None

        if stype in ("interval", ScheduleType.INTERVAL.value if hasattr(ScheduleType.INTERVAL, "value") else "interval"):
            if interval_minutes:
                from datetime import timedelta
                return now + timedelta(minutes=interval_minutes)

        # Handle string-based schedule types
        if stype == "daily" or stype == ScheduleType.DAILY.value:
            from datetime import timedelta
            return now + timedelta(days=1)
        if stype == "weekly":
            from datetime import timedelta
            return now + timedelta(weeks=1)
        if stype == "monthly":
            from datetime import timedelta
            # Approximate monthly as 30 days
            return now + timedelta(days=30)

        # Default: daily
        from datetime import timedelta
        return now + timedelta(days=1)

    @staticmethod
    def _to_response(schedule: ScheduledCollection) -> ScheduledCollectionResponse:
        """Map a ScheduledCollection ORM model to a response schema."""
        stype: str = schedule.schedule_type
        if not isinstance(stype, str):
            stype = stype.value

        return ScheduledCollectionResponse(
            id=schedule.id,
            template_id=schedule.template_id,
            schedule_type=stype,
            cron_expr=schedule.cron_expr,
            interval_minutes=schedule.interval_minutes,
            enabled=schedule.enabled,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_status=schedule.last_status,
            failure_count=schedule.failure_count,
            max_failures_before_pause=schedule.max_failures_before_pause,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )
