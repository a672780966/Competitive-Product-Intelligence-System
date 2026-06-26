"""CPIS V1 — Discovery Pydantic schemas for API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DiscoveryStatus, RecommendedCollector, RiskLevel, SourceType


# ── Request schemas ─────────────────────────────────────────────


class CreateDiscoverySessionRequest(BaseModel):
    """Request body for creating a new discovery session."""

    query: str = Field(..., min_length=1, max_length=1024, description="The search query")
    target_brand: str | None = Field(None, max_length=255, description="Brand to target")
    topic: str | None = Field(None, max_length=255, description="Topic or category")


class UpdateCandidateRequest(BaseModel):
    """Request body for updating a candidate's selected status."""

    selected: bool = Field(..., description="Whether the candidate is selected")


class BatchSelectRequest(BaseModel):
    """Request body for batch selecting/deselecting candidates."""

    candidate_ids: list[uuid.UUID] = Field(..., min_length=1, description="List of candidate IDs")
    selected: bool = Field(..., description="Whether to select or deselect")


class CreateTemplateFromSelectionRequest(BaseModel):
    """Request body for creating a CollectionTemplate from selected candidates."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    feishu_sync_enabled: bool = Field(default=False)


# ── Response schemas ────────────────────────────────────────────


class DiscoverySessionResponse(BaseModel):
    """Response model for a discovery session."""

    id: uuid.UUID
    query: str
    target_brand: str | None = None
    topic: str | None = None
    status: str
    model_provider: str | None = None
    search_provider: str | None = None
    error_message: str | None = None
    candidate_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SourceCandidateResponse(BaseModel):
    """Response model for a source candidate."""

    id: uuid.UUID
    discovery_session_id: uuid.UUID
    title: str
    url: str
    domain: str
    snippet: str | None = None
    thumbnail_url: str | None = None
    favicon_url: str | None = None
    source_type: str
    recommended_collector: str
    risk_level: str
    reason: str | None = None
    selected: bool = False
    raw_metadata: dict | None = None
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    """Response model for a discovery session with its candidates."""

    session: DiscoverySessionResponse
    candidates: list[SourceCandidateResponse]


class PaginatedCandidateResponse(BaseModel):
    """Paginated list of source candidates."""

    items: list[SourceCandidateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DiscoverySessionListResponse(BaseModel):
    """Paginated list of discovery sessions."""

    items: list[DiscoverySessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CreateTemplateFromSelectionResponse(BaseModel):
    """Response for creating a template from selected candidates."""

    template_id: uuid.UUID
    name: str
    candidate_count: int
    message: str
