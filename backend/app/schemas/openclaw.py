"""CPIS V1 — OpenClaw bridge schemas.

Defines the evidence_json envelope accepted from OpenClaw collector agent
and the CPIS ingestion response.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Inbound: evidence_batch from OpenClaw ────────────────────

class EvidenceSource(BaseModel):
    """Single source (URL) in an evidence batch."""
    source_id: str
    source_url: str | None = None
    url: str | None = None
    source_type: str | None = None
    collected_at: str | None = None


class EvidenceItem(BaseModel):
    """Single product item in an evidence batch."""
    item_id: str
    product_name: str | None = None
    asin: str | None = None
    brand: str | None = None
    product_url: str
    image_url: str | None = None
    pricing: dict | None = None
    ratings: dict | None = None
    ranking_type: str | None = None
    ranking_position: int | None = None
    ranking_source_id: str | None = None
    source_id: str | None = None
    source_ids: list[str] | None = None
    category: str | None = None
    description: str | None = None


class CollectionScope(BaseModel):
    """What was requested for collection."""
    max_items_per_ranking: int | None = None


class CollectionSummary(BaseModel):
    """Summary of the collection run."""
    total_items: int | None = None
    total_sources: int | None = None
    warnings: list[str] | None = None


class EvidenceBatch(BaseModel):
    """The evidence_batch payload from OpenClaw collector agent."""
    schema_version: str = "1.0"
    object_type: str = "evidence_batch"
    run_id: str
    status: str = "success"
    collection_scope: CollectionScope | None = None
    sources: list[EvidenceSource] = []
    items: list[EvidenceItem] = []
    collection_summary: CollectionSummary | None = None


class OpenClawEvidenceRequest(BaseModel):
    """Top-level request body for POST /api/v1/openclaw/evidence."""
    schema_version: str = "1.0"
    object_type: str = "agent_handoff"
    run_id: str
    from_agent: str = "cpis-info-collector"
    to_agent: str = "cpis-product-analyst"
    payload_type: str = "evidence_batch"
    payload: EvidenceBatch
    sent_at: str | None = None


# ── Outbound: ingestion result ───────────────────────────────

class IngestedItem(BaseModel):
    """Result of ingesting a single evidence item."""
    item_id: str
    task_id: uuid.UUID
    status: str
    error: str | None = None


class OpenClawEvidenceResponse(BaseModel):
    """Response from ingesting an OpenClaw evidence batch."""
    run_id: str
    status: str
    ingested: int
    items: list[IngestedItem]
    errors: list[str] = []
