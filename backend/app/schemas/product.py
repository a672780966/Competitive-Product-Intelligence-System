"""CPIS V1 - Product schemas for API responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class VersionSummaryResponse(BaseModel):
    """Summary of a product version."""

    id: uuid.UUID
    version_no: int
    overall_confidence: float | None
    ai_model: str | None
    prompt_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductSummaryResponse(BaseModel):
    """Summary of a product."""

    id: uuid.UUID
    unique_key: str
    brand: str | None
    name: str | None
    model: str | None
    category: str | None
    review_status: str
    current_version_id: uuid.UUID | None
    feishu_record_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductSummaryResponse):
    """Product detail including version history."""

    versions: list[VersionSummaryResponse] = []


class PaginatedProductResponse(BaseModel):
    """Paginated list of products."""

    items: list[ProductSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
