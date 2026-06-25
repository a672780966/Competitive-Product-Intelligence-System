"""
CPIS V1 — Human review service.

Manages the review lifecycle for product versions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import (
    AuditLog,
    Product,
    ProductEvidence,
    ProductVersion,
    ReviewRecord,
    SourceSnapshot,
)
from app.models.enums import ReviewStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.review import (
    ApproveRequest,
    EvidenceItem,
    PaginatedReviewResponse,
    ProductSummary,
    RejectRequest,
    ReviewDetailResponse,
    ReviewItemResponse,
    ReviewListQuery,
    SaveDraftRequest,
)

logger = get_logger(__name__)


class ReviewService:
    """Business logic for human review."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._product_repo = ProductRepository(db)

    async def list_reviews(
        self, query: ReviewListQuery,
    ) -> PaginatedReviewResponse:
        """List product versions waiting for or already reviewed.

        Shows versions where review_status is NEEDS_REVIEW, AUTO_APPROVED,
        or APPROVED — filterable by status.
        """
        # Join ProductVersion → Product to find versions needing review
        base_q = (
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
        )

        count_q = select(func.count(ProductVersion.id)).select_from(ProductVersion)
        count_q = count_q.join(Product, Product.id == ProductVersion.product_id)

        if query.status:
            base_q = base_q.where(Product.review_status == query.status.value)
            count_q = count_q.where(Product.review_status == query.status.value)
        else:
            # Show all non-completed statuses by default
            statuses = [s.value for s in (
                ReviewStatus.NEEDS_REVIEW,
                ReviewStatus.AUTO_APPROVED,
                ReviewStatus.PENDING,
            )]
            base_q = base_q.where(Product.review_status.in_(statuses))
            count_q = count_q.where(Product.review_status.in_(statuses))

        total = (await self._db.execute(count_q)).scalar() or 0

        base_q = (
            base_q
            .options(selectinload(ProductVersion.product))
            .order_by(ProductVersion.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        result = await self._db.execute(base_q)
        versions = list(result.scalars().all())

        items = [
            ReviewItemResponse(
                product_version_id=v.id,
                version_no=v.version_no,
                product=ProductSummary(
                    id=v.product.id,
                    unique_key=v.product.unique_key,
                    brand=v.product.brand,
                    name=v.product.name,
                    model=v.product.model,
                ),
                overall_confidence=v.overall_confidence,
                review_status=v.product.review_status,
                ai_model=v.ai_model,
                created_at=v.created_at,
            )
            for v in versions
        ]

        total_pages = max(1, (total + query.page_size - 1) // query.page_size)
        return PaginatedReviewResponse(
            items=items, total=total, page=query.page,
            page_size=query.page_size, total_pages=total_pages,
        )

    async def get_review_detail(
        self, version_id: uuid.UUID,
    ) -> ReviewDetailResponse | None:
        """Get full detail for the review panel."""
        result = await self._db.execute(
            select(ProductVersion)
            .where(ProductVersion.id == version_id)
            .options(
                selectinload(ProductVersion.product),
                selectinload(ProductVersion.evidences),
            ),
        )
        version = result.scalar_one_or_none()
        if version is None:
            return None

        # Get current review record for this version
        review_result = await self._db.execute(
            select(ReviewRecord)
            .where(ReviewRecord.product_version_id == version_id)
            .order_by(ReviewRecord.created_at.desc())
            .limit(1),
        )
        current_review = review_result.scalar_one_or_none()

        # Get source snapshot content
        snapshot = None
        if version.source_snapshot_id:
            snap_result = await self._db.execute(
                select(SourceSnapshot).where(
                    SourceSnapshot.id == version.source_snapshot_id,
                ),
            )
            snapshot = snap_result.scalar_one_or_none()

        return ReviewDetailResponse(
            product_version_id=version.id,
            version_no=version.version_no,
            product=ProductSummary(
                id=version.product.id,
                unique_key=version.product.unique_key,
                brand=version.product.brand,
                name=version.product.name,
                model=version.product.model,
            ),
            structured_data=version.structured_data or {},
            analysis_data=version.analysis_data or {},
            evidences=[
                EvidenceItem(
                    field_name=ev.field_name,
                    value=ev.value,
                    confidence=ev.confidence,
                    evidence_text=ev.evidence_text,
                )
                for ev in version.evidences
            ],
            overall_confidence=version.overall_confidence,
            ai_model=version.ai_model,
            review_status=version.product.review_status,
            current_review={
                "decision": current_review.decision,
                "comments": current_review.comments,
                "corrections": current_review.corrections,
                "changed_fields": current_review.changed_fields,
                "reviewer": current_review.reviewer,
                "created_at": current_review.created_at.isoformat(),
            } if current_review else None,
            cleaned_text=snapshot.cleaned_text if snapshot else None,
            source_url=snapshot.final_url if snapshot else version.product.source_url,
            source_text=snapshot.cleaned_text if snapshot else None,
        )

    async def save_draft(
        self, version_id: uuid.UUID, req: SaveDraftRequest, reviewer: str = "",
    ) -> ReviewDetailResponse | None:
        """Save corrections as a draft without approving or rejecting."""
        # Verify version exists
        version = await self._get_version(version_id)
        if version is None:
            return None

        # Upsert review record
        review = ReviewRecord(
            product_version_id=version_id,
            reviewer=reviewer or "unknown",
            decision=ReviewStatus.IN_REVIEW,
            comments=req.comments,
            corrections=req.corrections,
            changed_fields=list(req.corrections.keys()) if req.corrections else [],
        )
        self._db.add(review)
        await self._db.flush()
        logger.info("review_draft_saved", version_id=str(version_id))

        return await self.get_review_detail(version_id)

    async def approve(
        self, version_id: uuid.UUID, req: ApproveRequest, reviewer: str = "",
    ) -> ReviewDetailResponse | None:
        """Approve a version: set APPROVED, update product, log audit."""
        version = await self._get_version(version_id)
        if version is None:
            return None

        # Save review record
        review = ReviewRecord(
            product_version_id=version_id,
            reviewer=reviewer or "unknown",
            decision=ReviewStatus.APPROVED,
            comments=req.comments,
            corrections=req.corrections,
            changed_fields=list(req.corrections.keys()) if req.corrections else [],
        )
        self._db.add(review)

        # Update product status
        product = await self._product_repo.get_by_id(version.product_id)
        if product:
            await self._product_repo.update_review_status(
                product.id, ReviewStatus.APPROVED,
            )
            # Set as current version
            await self._product_repo.set_current_version(
                product.id, version_id,
            )

        # Apply corrections to structured_data if provided
        if req.corrections and version.structured_data:
            version.structured_data.update(req.corrections)

        # Audit log
        audit = AuditLog(
            actor=reviewer or "unknown",
            action="review.approve",
            resource_type="product_version",
            resource_id=str(version_id),
            detail=str({
                "product_id": str(version.product_id),
                "version_no": version.version_no,
            }),
        )
        self._db.add(audit)
        await self._db.flush()

        logger.info("review_approved", version_id=str(version_id))
        return await self.get_review_detail(version_id)

    async def reject(
        self, version_id: uuid.UUID, req: RejectRequest, reviewer: str = "",
    ) -> ReviewDetailResponse | None:
        """Reject a version: set REJECTED, log audit."""
        version = await self._get_version(version_id)
        if version is None:
            return None

        review = ReviewRecord(
            product_version_id=version_id,
            reviewer=reviewer or "unknown",
            decision=ReviewStatus.REJECTED,
            comments=req.comments,
        )
        self._db.add(review)

        product = await self._product_repo.get_by_id(version.product_id)
        if product:
            await self._product_repo.update_review_status(
                product.id, ReviewStatus.REJECTED,
            )

        audit = AuditLog(
            actor=reviewer or "unknown",
            action="review.reject",
            resource_type="product_version",
            resource_id=str(version_id),
            detail=str({
                "product_id": str(version.product_id),
                "version_no": version.version_no,
                "reason": req.comments,
            }),
        )
        self._db.add(audit)
        await self._db.flush()

        logger.info("review_rejected", version_id=str(version_id))
        return await self.get_review_detail(version_id)

    async def _get_version(self, version_id: uuid.UUID) -> ProductVersion | None:
        """Get a product version eagerly loaded with product."""
        result = await self._db.execute(
            select(ProductVersion)
            .where(ProductVersion.id == version_id)
            .options(selectinload(ProductVersion.product)),
        )
        return result.scalar_one_or_none()
