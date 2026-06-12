"""
CPIS V1 — Product and sync-record API routes.

Endpoints:
  GET   /api/v1/products                     — list with filters
  GET   /api/v1/products/{product_id}        — product detail
  GET   /api/v1/products/{product_id}/versions   — version history
  POST  /api/v1/products/{product_id}/recollect  — re-collect (create new task)
  POST  /api/v1/products/{product_id}/sync-feishu — manual sync
  GET   /api/v1/products/{product_id}/sync-records — sync history for a product
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import (
    ProductDetailResponse,
    ProductListQuery,
    ProductListResponse,
    ProductVersionItem,
    SyncRecordItem,
    SyncRecordListResponse,
)
from app.schemas.task import TaskResponse
from app.services.product_list_service import ProductListService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


# ── Product list ─────────────────────────────────────────────────


@router.get("", response_model=ProductListResponse)
async def list_products(
    keyword: str | None = Query(None, description="Search in brand/name/model"),
    brand: str | None = Query(None),
    category: str | None = Query(None),
    review_status: str | None = Query(None),
    created_from: str | None = Query(None),
    created_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """List products with optional filters."""
    query = ProductListQuery(
        keyword=keyword,
        brand=brand,
        category=category,
        review_status=review_status,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    service = ProductListService(db)
    return await service.list_products(query)


# ── Product detail ───────────────────────────────────────────────


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    """Get full product detail with current version, evidence, and history."""
    service = ProductListService(db)
    result = await service.get_product_detail(product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


# ── Version history ──────────────────────────────────────────────


@router.get("/{product_id}/versions", response_model=list[ProductVersionItem])
async def get_product_versions(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ProductVersionItem]:
    """Get version history for a product."""
    service = ProductListService(db)
    result = await service.get_versions(product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


# ── Recollect ────────────────────────────────────────────────────


@router.post("/{product_id}/recollect", response_model=TaskResponse)
async def recollect_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new collection task for the product's source URL."""
    service = ProductListService(db)
    result = await service.recollect(product_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found or has no source URL",
        )
    return result


# ── Sync to Feishu ───────────────────────────────────────────────


@router.post("/{product_id}/sync-feishu", response_model=SyncRecordItem)
async def sync_product_to_feishu(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SyncRecordItem:
    """Manually trigger a Feishu sync for a product."""
    service = ProductListService(db)
    result = await service.sync_to_feishu(product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


# ── Sync records for a product ───────────────────────────────────


@router.get("/{product_id}/sync-records", response_model=SyncRecordListResponse)
async def get_product_sync_records(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SyncRecordListResponse:
    """Get sync history for a specific product."""
    service = ProductListService(db)
    return await service.list_sync_records(
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
