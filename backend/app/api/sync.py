"""CPIS V1 - Sync record API routes.

Endpoints:
  GET  /api/v1/sync-records              - list sync records
  GET  /api/v1/sync-records/{record_id}  - sync record detail
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.sync_repository import SyncRepository
from app.schemas.sync import PaginatedSyncResponse, SyncRecordResponse

router = APIRouter(prefix="/api/v1/sync-records", tags=["sync-records"])


@router.get("", response_model=PaginatedSyncResponse)
async def list_sync_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSyncResponse:
    """List local sync records with optional filters."""
    repo = SyncRepository(db)
    items, total = await repo.list(
        status=status,
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedSyncResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{record_id}", response_model=SyncRecordResponse)
async def get_sync_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SyncRecordResponse:
    """Get local sync record detail."""
    repo = SyncRepository(db)
    record = await repo.get_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sync record not found")
    return record
