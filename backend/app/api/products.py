"""
CPIS V1 - Product API routes.

Endpoints:
  POST /api/v1/products                    - create product
  GET  /api/v1/products                    - list products
  GET  /api/v1/products/{product_id}       - product detail
  GET  /api/v1/products/{product_id}/versions - product versions
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Product
from app.models.enums import ReviewStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductSummaryResponse,
    VersionSummaryResponse,
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def _make_unique_key(brand: str | None, name: str) -> str:
    """Build a unique_key from brand and name."""
    brand_key = re.sub(r"[^a-z0-9]+", "-", (brand or "").lower()).strip("-") or "unknown"
    name_key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"demo.local/{brand_key}/{name_key}"


@router.post("", response_model=ProductSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProductSummaryResponse:
    """Create a new product. Returns 201 on success, 409 if duplicate."""
    repo = ProductRepository(db)
    unique_key = _make_unique_key(body.brand, body.name)

    existing = await repo.get_by_unique_key(unique_key)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with key '{unique_key}' already exists",
        )

    product = Product(
        unique_key=unique_key,
        brand=body.brand,
        name=body.name,
        model=body.model,
        category=body.category,
        source_url=body.source_url,
        review_status=ReviewStatus.AUTO_APPROVED.value,
    )
    product = await repo.create(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=PaginatedProductResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    domain: str | None = Query(None),
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedProductResponse:
    """List products with optional filters."""
    repo = ProductRepository(db)
    items, total = await repo.list(
        keyword=keyword,
        status=status,
        domain=domain,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedProductResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    """Get product detail including version history."""
    repo = ProductRepository(db)
    product = await repo.get_by_id_with_versions(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/{product_id}/versions", response_model=list[VersionSummaryResponse])
async def get_product_versions(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[VersionSummaryResponse]:
    """Get all versions for a product."""
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return await repo.get_versions(product_id)
