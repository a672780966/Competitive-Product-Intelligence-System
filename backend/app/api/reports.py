"""
CPIS V1 — Report generation API routes.

Endpoints:
  GET  /api/v1/reports/product/{product_id}     — single product report (Markdown)
  POST /api/v1/reports/compare                  — multi-product comparison (Markdown)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ComparisonBody(BaseModel):
    """Request body for comparison report."""

    product_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=20)


@router.get("/product/{product_id}")
async def single_product_report(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a single-product Markdown report."""
    service = ReportService(db)
    report = await service.single_product_report(product_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return PlainTextResponse(
        content=report,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=product-{product_id}.md",
        },
    )


@router.post("/compare")
async def comparison_report(
    body: ComparisonBody,
    db: AsyncSession = Depends(get_db),
):
    """Generate a multi-product comparison Markdown report."""
    service = ReportService(db)
    report = await service.comparison_report(body.product_ids)
    return PlainTextResponse(
        content=report,
        media_type="text/markdown",
        headers={
            "Content-Disposition": "attachment; filename=comparison-report.md",
        },
    )
