"""
CPIS V1 — Product repository (data access layer).

CRUD operations for Product, ProductVersion, and ProductEvidence.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Product, ProductEvidence, ProductVersion
from app.models.enums import ReviewStatus


class ProductRepository:
    """Data access for Product and related models."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Product ─────────────────────────────────────────────────

    async def get_by_unique_key(self, unique_key: str) -> Product | None:
        """Get a product by its unique key."""
        result = await self._db.execute(
            select(Product).where(Product.unique_key == unique_key),
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        """Get a product by primary key."""
        result = await self._db.execute(
            select(Product).where(Product.id == product_id),
        )
        return result.scalar_one_or_none()

    async def create(self, product: Product) -> Product:
        """Persist a new product."""
        self._db.add(product)
        await self._db.flush()
        return product

    async def update_review_status(
        self, product_id: uuid.UUID, status: ReviewStatus,
    ) -> Product | None:
        """Update product review status."""
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        product.review_status = status.value
        await self._db.flush()
        return product

    async def set_current_version(
        self, product_id: uuid.UUID, version_id: uuid.UUID,
    ) -> Product | None:
        """Set the current_version_id on a product."""
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        product.current_version_id = version_id
        await self._db.flush()
        return product

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """List products with pagination."""
        count_q = select(func.count(Product.id))
        total = (await self._db.execute(count_q)).scalar() or 0

        q = (
            select(Product)
            .order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(q)
        return list(result.scalars().all()), total

    # ── ProductVersion ──────────────────────────────────────────

    async def get_latest_version(self, product_id: uuid.UUID) -> ProductVersion | None:
        """Get the latest version for a product (by version_no DESC)."""
        result = await self._db.execute(
            select(ProductVersion)
            .where(ProductVersion.product_id == product_id)
            .order_by(ProductVersion.version_no.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def get_version_by_id(
        self, version_id: uuid.UUID,
    ) -> ProductVersion | None:
        """Get a version by primary key."""
        result = await self._db.execute(
            select(ProductVersion).where(ProductVersion.id == version_id),
        )
        return result.scalar_one_or_none()

    async def get_versions(
        self, product_id: uuid.UUID,
    ) -> list[ProductVersion]:
        """Get all versions for a product, ordered by version_no."""
        result = await self._db.execute(
            select(ProductVersion)
            .where(ProductVersion.product_id == product_id)
            .order_by(ProductVersion.version_no.asc()),
        )
        return list(result.scalars().all())

    async def create_version(self, version: ProductVersion) -> ProductVersion:
        """Persist a new version."""
        self._db.add(version)
        await self._db.flush()
        return version

    # ── ProductEvidence ─────────────────────────────────────────

    async def batch_save_evidence(
        self, evidences: list[ProductEvidence],
    ) -> list[ProductEvidence]:
        """Persist multiple evidence records."""
        for ev in evidences:
            self._db.add(ev)
        await self._db.flush()
        return evidences

    async def get_evidences(
        self, version_id: uuid.UUID,
    ) -> list[ProductEvidence]:
        """Get all evidences for a version."""
        result = await self._db.execute(
            select(ProductEvidence)
            .where(ProductEvidence.product_version_id == version_id)
            .order_by(ProductEvidence.created_at.asc()),
        )
        return list(result.scalars().all())
