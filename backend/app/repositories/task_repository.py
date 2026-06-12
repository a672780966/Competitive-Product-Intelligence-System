"""
CPIS V1 — Task repository (data access layer).

Provides CRUD operations on ``CollectionTask`` and ``TaskEvent`` models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CollectionTask, TaskEvent
from app.models.enums import TaskStatus


class TaskRepository:
    """Data access for CollectionTask and TaskEvent."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── CollectionTask ─────────────────────────────────────────

    async def create(self, task: CollectionTask) -> CollectionTask:
        """Persist a new task."""
        self._db.add(task)
        await self._db.flush()
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> CollectionTask | None:
        """Get a task by its primary key."""
        result = await self._db.execute(
            select(CollectionTask).where(CollectionTask.id == task_id),
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_events(self, task_id: uuid.UUID) -> CollectionTask | None:
        """Get a task with its event history eagerly loaded."""
        result = await self._db.execute(
            select(CollectionTask)
            .where(CollectionTask.id == task_id)
            .options(selectinload(CollectionTask.events)),
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: TaskStatus | None = None,
        domain: str | None = None,
        keyword: str | None = None,
        priority: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CollectionTask], int]:
        """List tasks with optional filters, returns (items, total_count)."""
        query = select(CollectionTask)
        count_query = select(func.count(CollectionTask.id))

        # Build filters
        conditions = []
        if status:
            conditions.append(CollectionTask.status == status.value)
        if domain:
            conditions.append(CollectionTask.domain == domain)
        if keyword:
            conditions.append(CollectionTask.source_url.ilike(f"%{keyword}%"))
        if priority:
            conditions.append(CollectionTask.priority == priority)
        if date_from:
            conditions.append(CollectionTask.created_at >= date_from)
        if date_to:
            conditions.append(CollectionTask.created_at <= date_to)

        # Apply filters
        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)

        # Count total
        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        # Order + paginate
        query = (
            query
            .order_by(CollectionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_status(
        self,
        task_id: uuid.UUID,
        status: TaskStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> CollectionTask | None:
        """Update task status and optionally set error info."""
        values: dict = {"status": status.value}
        if error_code:
            values["error_code"] = error_code
        if error_message:
            values["error_message"] = error_message

        if status in (TaskStatus.FETCHING,):
            values["started_at"] = datetime.now(timezone.utc)
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.PARTIAL_SUCCESS):
            values["finished_at"] = datetime.now(timezone.utc)

        stmt = (
            update(CollectionTask)
            .where(CollectionTask.id == task_id)
            .values(**values)
        )
        await self._db.execute(stmt)

        # Return refreshed task
        return await self.get_by_id(task_id)

    async def increment_retry(self, task_id: uuid.UUID) -> CollectionTask | None:
        """Increment retry count and reset status to PENDING."""
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        task.retry_count = (task.retry_count or 0) + 1
        task.status = TaskStatus.PENDING.value
        task.error_code = None
        task.error_message = None
        await self._db.flush()
        return task

    # ── TaskEvent ───────────────────────────────────────────────

    async def create_event(
        self,
        task_id: uuid.UUID,
        stage: str,
        status: TaskStatus,
        message: str | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
    ) -> TaskEvent:
        """Record a stage-transition event for a task."""
        event = TaskEvent(
            task_id=task_id,
            stage=stage,
            status=status.value,
            message=message,
            duration_ms=duration_ms,
            error_code=error_code,
        )
        self._db.add(event)
        await self._db.flush()
        return event

    async def get_events(self, task_id: uuid.UUID) -> list[TaskEvent]:
        """Get all events for a task, ordered by creation time."""
        result = await self._db.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.created_at.asc()),
        )
        return list(result.scalars().all())
