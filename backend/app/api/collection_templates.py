"""Collection Template API routes.

Endpoints:
  GET    /api/v1/collection-templates         — List templates
  GET    /api/v1/collection-templates/{id}    — Get template detail
  PATCH  /api/v1/collection-templates/{id}    — Update template
  POST   /api/v1/collection-templates/{id}/run — Execute template
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.enums import CollectionTemplateStatus
from app.schemas.template_schedule import (
    TemplateListResponse,
    TemplateResponse,
    TemplateRunResponse,
    TemplateUpdateRequest,
)
from app.services.template_service import TemplateService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collection-templates", tags=["collection-templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    status_filter: CollectionTemplateStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TemplateListResponse:
    """List collection templates with optional filters and pagination."""
    service = TemplateService(db)
    return await service.list_templates(
        status=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """Get a collection template by ID."""
    service = TemplateService(db)
    result = await service.get_template(template_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection template not found")
    return result


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    """Update a collection template's name, description, or status."""
    service = TemplateService(db)
    result = await service.update_template(template_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection template not found")
    return result


@router.post(
    "/{template_id}/run",
    response_model=TemplateRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TemplateRunResponse:
    """Execute a template immediately — creates CollectionTasks from its source_plan."""
    service = TemplateService(db)
    result = await service.run_template(template_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection template not found")
    return result
