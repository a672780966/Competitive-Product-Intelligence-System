"""CPIS V1 — Product and sync record schemas for API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.review import EvidenceItem

# ── Query ───────────────────────────────────────────────────────


class ProductListQuery(BaseModel):
    """Query parameters for listing products."""

    keyword: str | None = Field(None, description="Search in brand/name/model")
    brand: str | None = None
    category: str | None = None
    review_status: str | None = None
    sync_status: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── Response items ──────────────────────────────────────────────


class ProductItemResponse(BaseModel):
    """One product in a list response."""

    id: uuid.UUID
    unique_key: str
    brand: str | None = None
    name: str | None = None
    model: str | None = None
    category: str | None = None
    source_url: str | None = None
    review_status: str
    current_version_id: uuid.UUID | None = None
    feishu_record_id: str | None = None
    created_at: datetime
    updated_at: datetime
    overall_confidence: float | None = None

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Paginated product list."""

    items: list[ProductItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProductVersionItem(BaseModel):
    """One version in version history."""

    id: uuid.UUID
    version_no: int
    structured_data: dict = Field(default_factory=dict)
    analysis_data: dict = Field(default_factory=dict)
    ai_model: str | None = None
    prompt_version: str | None = None
    overall_confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncRecordItem(BaseModel):
    """One sync record in list responses."""

    id: uuid.UUID
    product_id: uuid.UUID
    sync_status: str
    sync_type: str
    feishu_record_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime
    synced_at: datetime | None = None
    product_brand: str | None = None
    product_name: str | None = None

    model_config = {"from_attributes": True}


class SyncRecordListResponse(BaseModel):
    """Paginated sync record list."""

    items: list[SyncRecordItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProductDetailResponse(BaseModel):
    """Full product detail with current version, evidence, and history."""

    id: uuid.UUID
    unique_key: str
    brand: str | None = None
    name: str | None = None
    model: str | None = None
    category: str | None = None
    source_url: str | None = None
    review_status: str
    feishu_record_id: str | None = None
    created_at: datetime
    updated_at: datetime

    # Current version detail
    current_version: ProductVersionItem | None = None

    # Evidences for current version
    evidences: list[EvidenceItem] = Field(default_factory=list)

    # Version history (summary list)
    versions: list[ProductVersionItem] = Field(default_factory=list)

    # Latest review record
    latest_review: dict | None = None

    # Latest sync record
    latest_sync: SyncRecordItem | None = None
