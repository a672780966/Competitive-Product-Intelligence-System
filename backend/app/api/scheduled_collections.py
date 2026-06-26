"""Scheduled Collection API routes.

Endpoints:
  GET    /api/v1/scheduled-collections              — List scheduled collections
  POST   /api/v1/scheduled-collections              — Create scheduled collection
  GET    /api/v1/scheduled-collections/{id}         — Get schedule detail
  PATCH  /api/v1/scheduled-collections/{id}         — Update schedule
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.template_schedule import (
    ScheduledCollectionCreateRequest,
    ScheduledCollectionDetailResponse,
    ScheduledCollectionListResponse,
    ScheduledCollectionResponse,
    ScheduledCollectionUpdateRequest,
)
from app.services.schedule_manager import ScheduleManager

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/scheduled-collections", tags=["scheduled-collections"])


@router.get("", response_model=ScheduledCollectionListResponse)
async def list_scheduled_collections(
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ScheduledCollectionListResponse:
    """List scheduled collections with optional filters and pagination."""
    manager = ScheduleManager(db)
    return await manager.list_schedules(
        enabled=enabled,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ScheduledCollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scheduled_collection(
    body: ScheduledCollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ScheduledCollectionResponse:
    """Create a new scheduled collection linked to a template."""
    manager = ScheduleManager(db)
    result = await manager.create_schedule(body)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection template not found")
    return result


@router.get("/{schedule_id}", response_model=ScheduledCollectionDetailResponse)
async def get_scheduled_collection(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ScheduledCollectionDetailResponse:
    """Get a scheduled collection with its template detail."""
    manager = ScheduleManager(db)
    result = await manager.get_schedule_detail(schedule_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scheduled collection not found")
    return result


@router.patch("/{schedule_id}", response_model=ScheduledCollectionResponse)
async def update_scheduled_collection(
    schedule_id: uuid.UUID,
    body: ScheduledCollectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ScheduledCollectionResponse:
    """Update a scheduled collection (enable/pause, reschedule)."""
    manager = ScheduleManager(db)
    result = await manager.update_schedule(schedule_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Scheduled collection not found")
    return result
