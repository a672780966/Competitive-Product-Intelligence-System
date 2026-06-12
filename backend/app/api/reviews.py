"""
CPIS V1 — Human review API routes.

Endpoints:
  GET   /api/v1/reviews                     — list reviews (paginated)
  GET   /api/v1/reviews/{version_id}        — review detail
  PUT   /api/v1/reviews/{version_id}/draft  — save draft
  POST  /api/v1/reviews/{version_id}/approve — approve
  POST  /api/v1/reviews/{version_id}/reject  — reject
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import ReviewStatus
from app.schemas.review import (
    ApproveRequest,
    PaginatedReviewResponse,
    RejectRequest,
    ReviewDetailResponse,
    ReviewListQuery,
    SaveDraftRequest,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.get("", response_model=PaginatedReviewResponse)
async def list_reviews(
    status: ReviewStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedReviewResponse:
    """List product versions for review."""
    query = ReviewListQuery(status=status, page=page, page_size=page_size)
    service = ReviewService(db)
    return await service.list_reviews(query)


@router.get("/{version_id}", response_model=ReviewDetailResponse)
async def get_review_detail(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReviewDetailResponse:
    """Get full review detail for a product version (left/right panel data)."""
    service = ReviewService(db)
    result = await service.get_review_detail(version_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@router.put("/{version_id}/draft", response_model=ReviewDetailResponse)
async def save_draft(
    version_id: uuid.UUID,
    body: SaveDraftRequest,
    db: AsyncSession = Depends(get_db),
) -> ReviewDetailResponse:
    """Save a review draft without finalizing."""
    service = ReviewService(db)
    result = await service.save_draft(version_id, body, reviewer="admin")
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@router.post("/{version_id}/approve", response_model=ReviewDetailResponse)
async def approve_version(
    version_id: uuid.UUID,
    body: ApproveRequest = ApproveRequest(),
    db: AsyncSession = Depends(get_db),
) -> ReviewDetailResponse:
    """Approve a product version — sets current_version and triggers sync."""
    service = ReviewService(db)
    result = await service.approve(version_id, body, reviewer="admin")
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return result


@router.post("/{version_id}/reject", response_model=ReviewDetailResponse)
async def reject_version(
    version_id: uuid.UUID,
    body: RejectRequest = RejectRequest(),
    db: AsyncSession = Depends(get_db),
) -> ReviewDetailResponse:
    """Reject a product version."""
    service = ReviewService(db)
    result = await service.reject(version_id, body, reviewer="admin")
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return result
