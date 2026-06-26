"""CPIS V1 — Discovery API routes.

Endpoints:
  POST   /api/v1/discovery/sessions              — create discovery session
  GET    /api/v1/discovery/sessions               — list sessions
  GET    /api/v1/discovery/sessions/{id}          — get session with candidates
  GET    /api/v1/discovery/sessions/{id}/candidates — list candidates with pagination
  PATCH  /api/v1/discovery/candidates/{id}         — update candidate selected status
  POST   /api/v1/discovery/sessions/{id}/select    — batch select/deselect
  POST   /api/v1/discovery/sessions/{id}/create-template — create template from selection
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.enums import DiscoveryStatus
from app.schemas.discovery import (
    BatchSelectRequest,
    CreateDiscoverySessionRequest,
    CreateTemplateFromSelectionRequest,
    CreateTemplateFromSelectionResponse,
    DiscoverySessionListResponse,
    DiscoverySessionResponse,
    PaginatedCandidateResponse,
    SessionDetailResponse,
    SourceCandidateResponse,
    UpdateCandidateRequest,
)
from app.services.discovery_service import DiscoveryService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.post(
    "/sessions",
    response_model=DiscoverySessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_discovery_session(
    body: CreateDiscoverySessionRequest,
    db: AsyncSession = Depends(get_db),
) -> DiscoverySessionResponse:
    """Create a discovery session, run search + analysis, return results."""
    service = DiscoveryService(db)
    return await service.create_session(body)


@router.get("/sessions", response_model=DiscoverySessionListResponse)
async def list_discovery_sessions(
    status_filter: DiscoveryStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DiscoverySessionListResponse:
    """List discovery sessions with optional status filter and pagination."""
    service = DiscoveryService(db)
    return await service.list_sessions(
        status=status_filter, page=page, page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_discovery_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """Get a discovery session with its candidates."""
    service = DiscoveryService(db)
    result = await service.get_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    return result


@router.get(
    "/sessions/{session_id}/candidates",
    response_model=PaginatedCandidateResponse,
)
async def list_session_candidates(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCandidateResponse:
    """List candidates for a session with pagination."""
    service = DiscoveryService(db)
    result = await service.list_candidates(
        session_id, page=page, page_size=page_size,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    return result


@router.patch(
    "/candidates/{candidate_id}",
    response_model=SourceCandidateResponse,
)
async def update_candidate(
    candidate_id: uuid.UUID,
    body: UpdateCandidateRequest,
    db: AsyncSession = Depends(get_db),
) -> SourceCandidateResponse:
    """Update a candidate's selected status."""
    service = DiscoveryService(db)
    result = await service.update_candidate_selection(
        candidate_id, body.selected,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


@router.post(
    "/sessions/{session_id}/select",
    response_model=dict,
)
async def batch_select_candidates(
    session_id: uuid.UUID,
    body: BatchSelectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Batch select or deselect candidates for a session."""
    service = DiscoveryService(db)
    count = await service.batch_select(
        session_id, body.candidate_ids, body.selected,
    )
    return {
        "updated": count,
        "selected": body.selected,
        "candidate_ids": [str(cid) for cid in body.candidate_ids],
    }


@router.post(
    "/sessions/{session_id}/create-template",
    response_model=CreateTemplateFromSelectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_from_selection(
    session_id: uuid.UUID,
    body: CreateTemplateFromSelectionRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateTemplateFromSelectionResponse:
    """Create a CollectionTemplate from the session's selected candidates."""
    service = DiscoveryService(db)
    result = await service.create_template_from_selection(session_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    return result
