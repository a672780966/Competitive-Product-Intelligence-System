"""
CPIS V1 — Report service.

Orchestrates report generation from product data in the database.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzers.report_generator import (
    generate_comparison_report,
    generate_single_product_report,
)
from app.core.logging import get_logger
from app.models import Product, ProductVersion

logger = get_logger(__name__)


class ReportService:
    """Generates competitive intelligence reports from database records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def single_product_report(self, product_id: uuid.UUID) -> str | None:
        """Generate a single-product Markdown report.

        Args:
            product_id: The product UUID.

        Returns:
            Markdown string, or None if product not found.
        """
        result = await self._db.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.versions)),
        )
        product = result.scalar_one_or_none()
        if product is None:
            return None

        # Get the current version (or latest)
        version = None
        if product.current_version_id:
            v_result = await self._db.execute(
                select(ProductVersion).where(
                    ProductVersion.id == product.current_version_id,
                ),
            )
            version = v_result.scalar_one_or_none()

        if version is None and product.versions:
            version = product.versions[-1]  # latest

        if version is None:
            return "# 产品竞品简报\n\n*暂无版本数据*"

        sd = version.structured_data or {}
        ad = version.analysis_data or {}
        product_name = sd.get("product_name") or product.name or ""

        return generate_single_product_report(
            product_name=product_name,
            brand=product.brand or sd.get("brand", ""),
            model=product.model or sd.get("model", ""),
            category=product.category or sd.get("category", ""),
            source_url=product.source_url or "",
            structured_data=sd,
            analysis_data=ad,
            version_no=version.version_no,
            collected_at=version.created_at,
        )

    async def comparison_report(self, product_ids: list[uuid.UUID]) -> str:
        """Generate a multi-product comparison Markdown report.

        Args:
            product_ids: List of product UUIDs to compare.

        Returns:
            Markdown string.
        """
        products_data: list[dict] = []

        for pid in product_ids:
            result = await self._db.execute(
                select(Product)
                .where(Product.id == pid)
                .options(selectinload(Product.versions)),
            )
            product = result.scalar_one_or_none()
            if product is None:
                continue

            version = None
            if product.current_version_id:
                v_result = await self._db.execute(
                    select(ProductVersion).where(
                        ProductVersion.id == product.current_version_id,
                    ),
                )
                version = v_result.scalar_one_or_none()

            if version is None and product.versions:
                version = product.versions[-1]

            sd = version.structured_data or {}
            ad = version.analysis_data or {}

            products_data.append({
                "name": sd.get("product_name") or product.name or "",
                "brand": product.brand or sd.get("brand", ""),
                "model": product.model or sd.get("model", ""),
                "category": product.category or sd.get("category", ""),
                "price_text": _price_summary(sd),
                "source_url": product.source_url or "",
                "analysis_data": ad,
                "version_no": version.version_no if version else 0,
            })

        return generate_comparison_report(products_data)


def _price_summary(sd: dict) -> str:
    """Short price string for comparison table."""
    parts = []
    currency = sd.get("currency", "")
    sale = sd.get("sale_price", "")
    orig = sd.get("original_price", "")
    if sale:
        parts.append(f"{currency}{sale}" if currency else sale)
    elif orig:
        parts.append(f"{currency}{orig}" if currency else orig)
    return " | ".join(parts) if parts else "—"
