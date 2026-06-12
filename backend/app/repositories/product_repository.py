"""
CPIS V1 — Product repository (data access layer).

CRUD operations for Product, ProductVersion, ProductEvidence,
and FeishuSyncRecord.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import FeishuSyncRecord, Product, ProductEvidence, ProductVersion, ReviewRecord
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

    async def list_with_filters(
        self,
        *,
        keyword: str | None = None,
        brand: str | None = None,
        category: str | None = None,
        review_status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """List products with filters, returns (items, total_count).

        Each product gets a transient ``_overall_confidence`` attribute
        from the current version for display purposes.
        """
        # Build filter conditions
        conditions = []
        if keyword:
            keyword_filter = (
                Product.name.ilike(f"%{keyword}%")
                | Product.brand.ilike(f"%{keyword}%")
                | Product.model.ilike(f"%{keyword}%")
                | Product.unique_key.ilike(f"%{keyword}%")
            )
            conditions.append(keyword_filter)
        if brand:
            conditions.append(Product.brand.ilike(f"%{brand}%"))
        if category:
            conditions.append(Product.category == category)
        if review_status:
            conditions.append(Product.review_status == review_status)
        if created_from:
            conditions.append(Product.created_at >= created_from)
        if created_to:
            conditions.append(Product.created_at <= created_to)

        # Count query (no join)
        count_q = select(func.count(Product.id))
        for cond in conditions:
            count_q = count_q.where(cond)
        total = (await self._db.execute(count_q)).scalar() or 0

        # Main query with left join to get current version confidence
        q = (
            select(Product, ProductVersion.overall_confidence)
            .outerjoin(
                ProductVersion,
                Product.current_version_id == ProductVersion.id,
            )
            .order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        for cond in conditions:
            q = q.where(cond)

        result = await self._db.execute(q)
        rows = result.all()

        items: list[Product] = []
        for product, confidence in rows:
            product._overall_confidence = confidence  # transient attr
            items.append(product)

        return items, total

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

    async def get_version_with_evidences(
        self, version_id: uuid.UUID,
    ) -> ProductVersion | None:
        """Get a version with its evidence eagerly loaded."""
        result = await self._db.execute(
            select(ProductVersion)
            .where(ProductVersion.id == version_id)
            .options(selectinload(ProductVersion.evidences)),
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

    # ── ReviewRecord ────────────────────────────────────────────

    async def get_latest_review(
        self, product_id: uuid.UUID,
    ) -> dict | None:
        """Get the latest review record for a product (via versions).

        Returns a dict with review metadata, or None.
        """
        result = await self._db.execute(
            select(ReviewRecord)
            .join(ProductVersion, ReviewRecord.product_version_id == ProductVersion.id)
            .where(ProductVersion.product_id == product_id)
            .order_by(ReviewRecord.created_at.desc())
            .limit(1),
        )
        review = result.scalar_one_or_none()
        if review is None:
            return None

        return {
            "id": str(review.id),
            "product_version_id": str(review.product_version_id),
            "reviewer": review.reviewer,
            "decision": review.decision.value if hasattr(review.decision, "value") else str(review.decision),
            "comments": review.comments,
            "changed_fields": review.changed_fields,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }

    # ── FeishuSyncRecord ────────────────────────────────────────

    async def get_latest_sync_record(
        self, product_id: uuid.UUID,
    ) -> FeishuSyncRecord | None:
        """Get the latest sync record for a product."""
        result = await self._db.execute(
            select(FeishuSyncRecord)
            .where(FeishuSyncRecord.product_id == product_id)
            .order_by(FeishuSyncRecord.created_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def get_sync_record_by_id(
        self, sync_id: uuid.UUID,
    ) -> FeishuSyncRecord | None:
        """Get a sync record by primary key."""
        result = await self._db.execute(
            select(FeishuSyncRecord).where(FeishuSyncRecord.id == sync_id),
        )
        return result.scalar_one_or_none()

    async def list_sync_records(
        self,
        *,
        product_id: uuid.UUID | None = None,
        sync_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FeishuSyncRecord], int]:
        """List sync records with optional filters, returns (items, total)."""
        conditions = []
        if product_id:
            conditions.append(FeishuSyncRecord.product_id == product_id)
        if sync_status:
            conditions.append(FeishuSyncRecord.sync_status == sync_status)

        # Count
        count_q = select(func.count(FeishuSyncRecord.id))
        for cond in conditions:
            count_q = count_q.where(cond)
        total = (await self._db.execute(count_q)).scalar() or 0

        # Query with product info join
        q = (
            select(
                FeishuSyncRecord,
                Product.brand,
                Product.name,
            )
            .join(Product, FeishuSyncRecord.product_id == Product.id)
            .order_by(FeishuSyncRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        for cond in conditions:
            q = q.where(cond)

        result = await self._db.execute(q)
        rows = result.all()

        items: list[FeishuSyncRecord] = []
        for record, brand, name in rows:
            record._product_brand = brand
            record._product_name = name
            items.append(record)

        return items, total
