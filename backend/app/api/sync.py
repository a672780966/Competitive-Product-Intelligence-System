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
from app.repositories.product_repository import ProductRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.sync import PaginatedSyncResponse, SyncAllResponse, SyncRecordResponse
from app.services.feishu_sync_service import FeishuSyncService

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


@router.post("/sync-product/{product_id}", response_model=SyncRecordResponse)
async def trigger_sync_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SyncRecordResponse:
    """Trigger a single product sync to Feishu Bitable.

    Returns the sync record — HTTP 200 even if the sync itself fails,
    because the failure is recorded in the record. Returns 404 only
    when the product does not exist.
    """
    prod_repo = ProductRepository(db)
    product = await prod_repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    service = FeishuSyncService(db)
    record = await service.sync_product(product_id)
    return record


@router.post("/sync-all", response_model=SyncAllResponse)
async def trigger_sync_all(
    db: AsyncSession = Depends(get_db),
) -> SyncAllResponse:
    """Trigger sync for all pending products.

    Pending products are those with ``auto_approved`` or ``approved``
    status and no ``feishu_record_id``. Returns a summary including
    how many products were processed and the per-record results.
    """
    service = FeishuSyncService(db)
    records = await service.sync_all_pending()
    return SyncAllResponse(
        synced_count=len(records),
        records=[SyncRecordResponse.model_validate(r) for r in records],
    )
