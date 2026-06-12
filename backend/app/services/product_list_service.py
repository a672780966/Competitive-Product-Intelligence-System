"""
CPIS V1 — Product list & detail service.

Handles listing, detail view, recollect, and sync trigger operations.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import SyncStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductDetailResponse,
    ProductItemResponse,
    ProductListQuery,
    ProductListResponse,
    ProductVersionItem,
    SyncRecordItem,
    SyncRecordListResponse,
)
from app.schemas.review import EvidenceItem
from app.schemas.task import CreateTaskRequest, TaskResponse
from app.services.feishu_sync_service import FeishuSyncService
from app.services.task_service import TaskService

logger = get_logger(__name__)


class ProductListService:
    """Business logic for product list, detail, and related operations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ProductRepository(db)

    # ── List ─────────────────────────────────────────────────────

    async def list_products(self, query: ProductListQuery) -> ProductListResponse:
        """List products with filters and pagination."""
        items, total = await self._repo.list_with_filters(
            keyword=query.keyword,
            brand=query.brand,
            category=query.category,
            review_status=query.review_status,
            created_from=query.created_from,
            created_to=query.created_to,
            page=query.page,
            page_size=query.page_size,
        )
        total_pages = max(1, (total + query.page_size - 1) // query.page_size)

        return ProductListResponse(
            items=[self._product_to_item(p) for p in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
        )

    # ── Detail ───────────────────────────────────────────────────

    async def get_product_detail(
        self, product_id: uuid.UUID,
    ) -> ProductDetailResponse | None:
        """Get full product detail with current version, evidence, and history."""
        product = await self._repo.get_by_id(product_id)
        if product is None:
            return None

        # Current version with evidence
        current_version = None
        evidences: list[EvidenceItem] = []
        if product.current_version_id:
            cv = await self._repo.get_version_with_evidences(
                product.current_version_id,
            )
            if cv:
                current_version = self._version_to_item(cv)
                evidences = [
                    EvidenceItem(
                        field_name=ev.field_name,
                        value=ev.value,
                        confidence=ev.confidence,
                        evidence_text=ev.evidence_text,
                    )
                    for ev in cv.evidences
                ]

        # Version history
        versions = [
            self._version_to_item(v)
            for v in await self._repo.get_versions(product_id)
        ]

        # Latest review record
        latest_review = await self._repo.get_latest_review(product_id)

        # Latest sync record
        latest_sync_rec = await self._repo.get_latest_sync_record(product_id)

        return ProductDetailResponse(
            id=product.id,
            unique_key=product.unique_key,
            brand=product.brand,
            name=product.name,
            model=product.model,
            category=product.category,
            source_url=product.source_url,
            review_status=product.review_status,
            feishu_record_id=product.feishu_record_id,
            created_at=product.created_at,
            updated_at=product.updated_at,
            current_version=current_version,
            evidences=evidences,
            versions=versions,
            latest_review=latest_review,
            latest_sync=self._sync_to_item(latest_sync_rec) if latest_sync_rec else None,
        )

    # ── Version history ──────────────────────────────────────────

    async def get_versions(
        self, product_id: uuid.UUID,
    ) -> list[ProductVersionItem] | None:
        """Get version history for a product."""
        product = await self._repo.get_by_id(product_id)
        if product is None:
            return None
        versions = await self._repo.get_versions(product_id)
        return [self._version_to_item(v) for v in versions]

    # ── Recollect ────────────────────────────────────────────────

    async def recollect(
        self, product_id: uuid.UUID,
    ) -> TaskResponse | None:
        """Create a new collection task for the product's source URL."""
        product = await self._repo.get_by_id(product_id)
        if product is None or not product.source_url:
            return None

        req = CreateTaskRequest(
            source_url=product.source_url,
            category_hint=product.category,
            created_by="system",
        )
        task_service = TaskService(self._db)
        return await task_service.create_task(req)

    # ── Sync to Feishu ───────────────────────────────────────────

    async def sync_to_feishu(
        self, product_id: uuid.UUID,
    ) -> SyncRecordItem | None:
        """Trigger a manual Feishu sync for a product."""
        product = await self._repo.get_by_id(product_id)
        if product is None:
            return None

        feishu_service = FeishuSyncService(self._db)
        record = await feishu_service.sync_product(product_id)
        return self._sync_to_item(record)

    # ── Sync records ─────────────────────────────────────────────

    async def list_sync_records(
        self,
        product_id: uuid.UUID | None = None,
        sync_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SyncRecordListResponse:
        """List sync records with optional filters."""
        items, total = await self._repo.list_sync_records(
            product_id=product_id,
            sync_status=sync_status,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)

        return SyncRecordListResponse(
            items=[self._sync_to_item(s) for s in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def retry_sync(
        self, sync_id: uuid.UUID,
    ) -> SyncRecordItem | None:
        """Retry a failed sync record by triggering a new sync."""
        record = await self._repo.get_sync_record_by_id(sync_id)
        if record is None:
            return None
        if record.sync_status != SyncStatus.FAILED.value:
            return self._sync_to_item(record)

        # Create a new sync attempt via FeishuSyncService
        feishu_service = FeishuSyncService(self._db)
        new_record = await feishu_service.sync_product(record.product_id)
        return self._sync_to_item(new_record)

    # ── Mappers ──────────────────────────────────────────────────

    @staticmethod
    def _product_to_item(product) -> ProductItemResponse:
        confidence = getattr(product, "_overall_confidence", None)
        return ProductItemResponse(
            id=product.id,
            unique_key=product.unique_key,
            brand=product.brand,
            name=product.name,
            model=product.model,
            category=product.category,
            source_url=product.source_url,
            review_status=product.review_status,
            current_version_id=product.current_version_id,
            feishu_record_id=product.feishu_record_id,
            created_at=product.created_at,
            updated_at=product.updated_at,
            overall_confidence=confidence,
        )

    @staticmethod
    def _version_to_item(version) -> ProductVersionItem:
        return ProductVersionItem(
            id=version.id,
            version_no=version.version_no,
            structured_data=version.structured_data or {},
            analysis_data=version.analysis_data or {},
            ai_model=version.ai_model,
            prompt_version=version.prompt_version,
            overall_confidence=version.overall_confidence,
            created_at=version.created_at,
        )

    @staticmethod
    def _sync_to_item(record) -> SyncRecordItem:
        brand = getattr(record, "_product_brand", None)
        name = getattr(record, "_product_name", None)
        return SyncRecordItem(
            id=record.id,
            product_id=record.product_id,
            sync_status=record.sync_status if isinstance(record.sync_status, str) else record.sync_status.value,
            sync_type=record.sync_type,
            feishu_record_id=record.feishu_record_id,
            error_message=record.error_message,
            retry_count=record.retry_count,
            created_at=record.created_at,
            synced_at=record.synced_at,
            product_brand=brand,
            product_name=name,
        )
