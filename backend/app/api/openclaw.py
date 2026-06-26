"""
CPIS V1 — OpenClaw bridge API routes.

Endpoints:
  POST /api/v1/openclaw/evidence  — ingest evidence_batch from OpenClaw collector
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas.openclaw import (
    OpenClawEvidenceRequest,
    OpenClawEvidenceResponse,
)
from app.services.openclaw_bridge_service import OpenClawBridgeService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/openclaw", tags=["openclaw-bridge"])


@router.post(
    "/evidence",
    response_model=OpenClawEvidenceResponse,
    status_code=status.HTTP_200_OK,
)
async def ingest_evidence(
    body: OpenClawEvidenceRequest,
    db: AsyncSession = Depends(get_db),
) -> OpenClawEvidenceResponse:
    """Ingest evidence_batch from OpenClaw collector agent.

    Creates CollectionTask + Product/ProductVersion for each item.
    This is the *only* entry point for OpenClaw data into CPIS.
    OpenClaw must not write directly to CPIS database or Feishu.
    """
    service = OpenClawBridgeService(db)
    result = await service.ingest_evidence(body)
    logger.info(
        "openclaw_evidence_ingested",
        run_id=body.run_id,
        ingested=result.ingested,
        total=len(body.payload.items),
    )
    return result
