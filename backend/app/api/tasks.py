"""
CPIS V1 — Collection Task API routes.

Endpoints:
  POST   /api/v1/collection-tasks          — create single task
  POST   /api/v1/collection-tasks/batch    — batch create
  GET    /api/v1/collection-tasks          — list with filters
  GET    /api/v1/collection-tasks/{id}     — task detail
  POST   /api/v1/collection-tasks/{id}/retry   — retry failed task
  POST   /api/v1/collection-tasks/{id}/cancel  — cancel task
  GET    /api/v1/collection-tasks/{id}/events  — task event history
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.task import (
    BatchCreateTaskRequest,
    BatchCreateTaskResponse,
    CreateTaskRequest,
    PaginatedTaskResponse,
    TaskDetailResponse,
    TaskEventResponse,
    TaskListQuery,
    TaskResponse,
)
from app.services.task_service import TaskService
from app.models.enums import TaskPriority, TaskStatus

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collection-tasks", tags=["collection-tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a single collection task."""
    service = TaskService(db)
    return await service.create_task(body)


@router.post("/batch", response_model=BatchCreateTaskResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_tasks(
    body: BatchCreateTaskRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchCreateTaskResponse:
    """Batch-create collection tasks (up to 100 per request)."""
    service = TaskService(db)
    tasks = await service.batch_create(body)
    return BatchCreateTaskResponse(created=len(tasks), tasks=tasks)


@router.get("", response_model=PaginatedTaskResponse)
async def list_tasks(
    status_filter: TaskStatus | None = Query(None, alias="status"),
    domain: str | None = Query(None),
    keyword: str | None = Query(None),
    priority: TaskPriority | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTaskResponse:
    """List collection tasks with optional filters."""
    query = TaskListQuery(
        status=status_filter,
        domain=domain,
        keyword=keyword,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    service = TaskService(db)
    return await service.list_tasks(query)


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    """Get task detail including event history."""
    service = TaskService(db)
    result = await service.get_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.post("/{task_id}/retry", response_model=TaskDetailResponse)
async def retry_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    """Retry a failed or blocked task."""
    service = TaskService(db)
    result = await service.retry_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.post("/{task_id}/cancel", response_model=TaskDetailResponse)
async def cancel_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    """Cancel a pending or in-progress task."""
    service = TaskService(db)
    result = await service.cancel_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.get("/{task_id}/events", response_model=list[TaskEventResponse])
async def get_task_events(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[TaskEventResponse]:
    """Get event history for a task."""
    service = TaskService(db)
    result = await service.get_events(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result
