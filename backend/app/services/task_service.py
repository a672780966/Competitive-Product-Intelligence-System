"""
CPIS V1 — Task service (business logic layer).

Orchestrates task lifecycle operations:
- Create single / batch tasks (with URL validation)
- Query / retry / cancel
- Event logging
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import CollectionTask, AuditLog
from app.models.enums import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.collector_execution_report import CollectorExecutionReportResponse
from app.schemas.task import (
    BatchCreateTaskRequest,
    CreateTaskRequest,
    PaginatedTaskResponse,
    PipelineStageStatus,
    PipelineStatusResponse,
    SnapshotResponse,
    TaskDetailResponse,
    TaskEventResponse,
    TaskListQuery,
    TaskResponse,
)
from app.services.url_validator import validate_url
from app.schemas import UrlValidationInput

logger = get_logger(__name__)


class TaskService:
    """Business logic for collection task management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = TaskRepository(db)

    # ── Create ──────────────────────────────────────────────────

    async def create_task(self, req: CreateTaskRequest) -> TaskResponse:
        """Create a single collection task and run URL validation.

        The task is created with PENDING status, then URL validation
        is performed. If validation fails, the task moves to BLOCKED.
        """
        task = CollectionTask(
            source_url=req.source_url,
            category_hint=req.category_hint,
            language_hint=req.language_hint,
            priority=req.priority.value if isinstance(req.priority, TaskPriority) else req.priority,
            auto_sync_feishu=req.auto_sync_feishu,
            created_by=req.created_by,
            status=TaskStatus.PENDING,
        )
        task = await self._repo.create(task)
        logger.info("task_created", task_id=str(task.id), url=task.source_url)

        # Audit log
        self._db.add(AuditLog(
            actor=req.created_by or "system",
            action="task.create",
            resource_type="task",
            resource_id=str(task.id),
            detail=f"source_url={task.source_url}",
        ))

        # Record creation event
        await self._repo.create_event(
            task_id=task.id,
            stage="creation",
            status=TaskStatus.PENDING,
            message="Task created",
        )

        # Run URL validation
        await self._run_validation(task)

        return self._task_to_response(task)

    async def batch_create(self, req: BatchCreateTaskRequest) -> list[TaskResponse]:
        """Create multiple tasks in one request."""
        responses: list[TaskResponse] = []
        for item in req.tasks:
            resp = await self.create_task(item)
            responses.append(resp)
        return responses

    # ── Query ───────────────────────────────────────────────────

    async def get_task(self, task_id: uuid.UUID) -> TaskDetailResponse | None:
        """Get task detail with event history and execution reports."""
        task = await self._repo.get_by_id_with_events(task_id)
        if task is None:
            return None
        detail = self._task_to_detail(task)
        reports = await self._repo.get_execution_reports(task_id)
        detail.execution_reports = [CollectorExecutionReportResponse.model_validate(r) for r in reports]
        return detail

    async def list_tasks(self, query: TaskListQuery) -> PaginatedTaskResponse:
        """List tasks with filters and pagination."""
        items, total = await self._repo.list(
            status=query.status,
            domain=query.domain,
            keyword=query.keyword,
            priority=query.priority.value if isinstance(query.priority, TaskPriority) else query.priority,
            date_from=query.date_from,
            date_to=query.date_to,
            page=query.page,
            page_size=query.page_size,
        )
        total_pages = max(1, (total + query.page_size - 1) // query.page_size)

        return PaginatedTaskResponse(
            items=[self._task_to_response(t) for t in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
        )

    # ── Mutations ───────────────────────────────────────────────

    async def retry_task(self, task_id: uuid.UUID) -> TaskDetailResponse | None:
        """Reset a failed/blocked task back to the pipeline."""
        task = await self._repo.get_by_id(task_id)
        if task is None:
            return None
        if task.status not in (
            TaskStatus.FAILED.value,
            TaskStatus.BLOCKED.value,
            TaskStatus.PARTIAL_SUCCESS.value,
        ):
            logger.warning("retry_invalid_status", task_id=str(task_id), status=task.status)
            return self._task_to_detail(task)

        task = await self._repo.increment_retry(task_id)
        await self._repo.create_event(
            task_id=task_id,
            stage="retry",
            status=TaskStatus.PENDING,
            message=f"Retry attempt {task.retry_count}",
        )
        logger.info("task_retried", task_id=str(task_id), attempt=task.retry_count)

        # Audit log
        self._db.add(AuditLog(
            actor="system", action="task.retry",
            resource_type="task", resource_id=str(task_id),
            detail=f"attempt={task.retry_count}",
        ))

        # Re-run validation
        await self._run_validation(task)

        return await self.get_task(task_id)

    async def cancel_task(self, task_id: uuid.UUID) -> TaskDetailResponse | None:
        """Cancel a pending or in-progress task."""
        task = await self._repo.get_by_id(task_id)
        if task is None:
            return None
        if task.status == TaskStatus.COMPLETED.value:
            logger.warning("cancel_completed_task", task_id=str(task_id))
            return self._task_to_detail(task)

        await self._repo.update_status(task_id, TaskStatus.CANCELLED)
        await self._repo.create_event(
            task_id=task_id,
            stage="cancellation",
            status=TaskStatus.CANCELLED,
            message="Task cancelled by user",
        )
        logger.info("task_cancelled", task_id=str(task_id))

        # Audit log
        self._db.add(AuditLog(
            actor="system", action="task.cancel",
            resource_type="task", resource_id=str(task_id),
            detail="Cancelled by user",
        ))
        return await self.get_task(task_id)

    async def get_events(self, task_id: uuid.UUID) -> list[TaskEventResponse] | None:
        """Get the event history for a task."""
        task = await self._repo.get_by_id(task_id)
        if task is None:
            return None
        events = await self._repo.get_events(task_id)
        return [self._event_to_response(e) for e in events]

    # ── Internal ────────────────────────────────────────────────

    async def _run_validation(self, task: CollectionTask) -> None:
        """Run URL validation and update task status accordingly."""
        await self._repo.update_status(task.id, TaskStatus.VALIDATING)
        await self._repo.create_event(
            task_id=task.id,
            stage="validation",
            status=TaskStatus.VALIDATING,
            message="Starting URL validation",
        )

        try:
            validation_input = UrlValidationInput(
                source_url=task.source_url,
                category_hint=task.category_hint,
                language_hint=task.language_hint,
            )
            result = await validate_url(validation_input)
        except Exception as exc:
            logger.error("validation_error", task_id=str(task.id), error=str(exc))
            await self._repo.update_status(
                task.id, TaskStatus.FAILED,
                error_code="VALIDATION_ERROR",
                error_message=str(exc),
            )
            await self._repo.create_event(
                task_id=task.id,
                stage="validation",
                status=TaskStatus.FAILED,
                message=f"Validation error: {exc}",
                error_code="VALIDATION_ERROR",
            )
            return

        # Update task with normalized URL
        task.normalized_url = result.normalized_url
        task.domain = result.domain
        await self._repo._db.flush()

        if result.status.value == "passed":
            await self._repo.update_status(task.id, TaskStatus.PENDING)
            await self._repo.create_event(
                task_id=task.id,
                stage="validation",
                status=TaskStatus.PENDING,
                message="URL validation passed — ready for collection",
            )
            from app.tasks.collection import collect_url
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, collect_url.delay, str(task.id), task.source_url)
            await self._repo.create_event(
                task_id=task.id,
                stage="enqueue",
                status=TaskStatus.PENDING,
                message="Task enqueued for collection",
            )
        else:
            status = TaskStatus.BLOCKED
            await self._repo.update_status(
                task.id, status,
                error_code=result.error_code.value if result.error_code else None,
                error_message=result.error_message,
            )
            await self._repo.create_event(
                task_id=task.id,
                stage="validation",
                status=status,
                message=result.error_message or "URL validation failed",
                error_code=result.error_code.value if result.error_code else None,
            )

    # ── Mappers ─────────────────────────────────────────────────

    @staticmethod
    def _task_to_response(task: CollectionTask) -> TaskResponse:
        return TaskResponse(
            id=task.id,
            source_url=task.source_url,
            normalized_url=task.normalized_url,
            domain=task.domain,
            status=task.status if isinstance(task.status, str) else task.status.value,
            priority=task.priority if isinstance(task.priority, int) else task.priority.value,
            category_hint=task.category_hint,
            language_hint=task.language_hint,
            auto_sync_feishu=task.auto_sync_feishu,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            error_code=task.error_code,
            error_message=task.error_message,
            created_by=task.created_by,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _task_to_detail(task: CollectionTask) -> TaskDetailResponse:
        base = TaskService._task_to_response(task)
        task_events = sorted(task.events, key=lambda event: event.created_at)
        events = [TaskService._event_to_response(e) for e in task_events]
        latest_by_stage: dict[str, TaskEventResponse] = {}
        for event in events:
            latest_by_stage[event.stage] = event

        return TaskDetailResponse(
            **base.model_dump(),
            events=events,
            snapshot=SnapshotResponse.model_validate(task.snapshot) if task.snapshot else None,
            pipeline_status=PipelineStatusResponse(
                stages=[
                    PipelineStageStatus(
                        stage=event.stage,
                        status=event.status,
                        error_code=event.error_code,
                        error_message=event.message if event.error_code else None,
                    )
                    for event in latest_by_stage.values()
                ],
                current_stage=events[-1].stage if events else None,
                overall_status=base.status,
                retry_count=base.retry_count,
                max_retries=base.max_retries,
            ),
        )

    @staticmethod
    def _event_to_response(event) -> TaskEventResponse:
        return TaskEventResponse(
            id=event.id,
            stage=event.stage,
            status=event.status,
            message=event.message,
            duration_ms=event.duration_ms,
            error_code=event.error_code,
            created_at=event.created_at,
        )
