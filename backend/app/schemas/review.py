"""CPIS V1 — Human review schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ReviewStatus

# ── Query ───────────────────────────────────────────────────────


class ReviewListQuery(BaseModel):
    """Query parameters for listing reviews."""

    status: ReviewStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── Summary item ────────────────────────────────────────────────


class ProductSummary(BaseModel):
    """Brief product info for review lists."""

    id: uuid.UUID
    unique_key: str
    brand: str | None = None
    name: str | None = None
    model: str | None = None

    model_config = {"from_attributes": True}


class ReviewItemResponse(BaseModel):
    """One item in the review list."""

    product_version_id: uuid.UUID
    version_no: int
    product: ProductSummary
    overall_confidence: float | None = 0.0
    review_status: str
    ai_model: str | None = None
    created_at: datetime


class PaginatedReviewResponse(BaseModel):
    """Paginated review list."""

    items: list[ReviewItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Detail ──────────────────────────────────────────────────────


class EvidenceItem(BaseModel):
    """Evidence for one extracted field."""

    field_name: str
    value: str | None = None
    confidence: float | None = None
    evidence_text: str | None = None


class ReviewDetailResponse(BaseModel):
    """Full detail for the review panel."""

    product_version_id: uuid.UUID
    version_no: int
    product: ProductSummary
    structured_data: dict = Field(default_factory=dict)
    analysis_data: dict = Field(default_factory=dict)
    evidences: list[EvidenceItem] = Field(default_factory=list)
    overall_confidence: float | None = 0.0
    ai_model: str | None = None
    review_status: str
    current_review: dict | None = None
    cleaned_text: str | None = None
    source_url: str | None = None


# ── Mutation requests ───────────────────────────────────────────


class SaveDraftRequest(BaseModel):
    """Save a review draft without finalizing."""

    corrections: dict = Field(default_factory=dict)
    comments: str | None = None


class ApproveRequest(BaseModel):
    """Approve a product version."""

    corrections: dict | None = None
    comments: str | None = None


class RejectRequest(BaseModel):
    """Reject a product version."""

    comments: str | None = None
