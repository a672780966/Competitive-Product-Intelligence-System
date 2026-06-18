"""
CPIS V1 — Sync record API routes.

Endpoints:
  GET  /api/v1/sync-records                — global sync record list
  POST /api/v1/sync-records/{sync_id}/retry — retry failed sync
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import SyncRecordItem, SyncRecordListResponse
from app.services.product_list_service import ProductListService

router = APIRouter(prefix="/api/v1/sync-records", tags=["sync-records"])


@router.get("", response_model=SyncRecordListResponse)
async def list_sync_records(
    sync_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SyncRecordListResponse:
    """List all sync records globally with optional status filter."""
    service = ProductListService(db)
    return await service.list_sync_records(
        sync_status=sync_status,
        page=page,
        page_size=page_size,
    )


@router.post("/{sync_id}/retry", response_model=SyncRecordItem)
async def retry_sync_record(
    sync_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SyncRecordItem:
    """Retry a failed sync record."""
    service = ProductListService(db)
    result = await service.retry_sync(sync_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Sync record not found")
    return result
