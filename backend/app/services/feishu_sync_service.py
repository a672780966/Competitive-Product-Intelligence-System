"""
CPIS V1 — Feishu sync service.

Orchestrates syncing approved products to Feishu Bitable.
Tracks sync status in ``feishu_sync_records`` table.
"""

from __future__ import annotations

import uuid

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.feishu_bitable import FeishuBitable
from app.integrations.feishu_client import FeishuApiError
from app.models import FeishuSyncRecord, Product, ProductVersion
from app.models.enums import SyncStatus
from app.repositories.product_repository import ProductRepository

logger = get_logger(__name__)


class FeishuSyncService:
    """Orchestration for syncing products to Feishu Bitable."""

    def __init__(
        self,
        db: AsyncSession,
        bitable: FeishuBitable | None = None,
    ) -> None:
        self._db = db
        self._repo = ProductRepository(db)
        self._bitable = bitable or FeishuBitable()

    async def sync_product(self, product_id: uuid.UUID) -> FeishuSyncRecord:
        """Sync a product to Feishu Bitable.

        Looks up the product + latest version, calls the bitable upsert,
        and records the sync result.
        """
        # 1. Look up product and version
        product = await self._repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")

        version = await self._repo.get_latest_version(product.id)
        if version is None:
            raise ValueError(f"No version found for product: {product_id}")

        # 2. Create sync record
        sync = FeishuSyncRecord(
            product_id=product.id,
            sync_status=SyncStatus.SYNCING,
            sync_type="bitable",
        )
        self._db.add(sync)
        await self._db.flush()

        # 3. Call Feishu API
        try:
            result = await self._bitable.upsert_product(
                structured_data=version.structured_data or {},
                analysis_data=version.analysis_data or {},
                unique_key=product.unique_key,
                version_no=version.version_no,
                source_url=product.source_url or "",
            )

            # 4. Update product and sync record
            feishu_record_id = result["record_id"]
            sync.sync_status = SyncStatus.SUCCESS.value
            sync.feishu_record_id = feishu_record_id
            sync.synced_at = datetime.now(timezone.utc)
            product.feishu_record_id = feishu_record_id
            await self._db.flush()

            logger.info(
                "feishu_sync_success",
                product_id=str(product.id),
                action=result["action"],
                record_id=feishu_record_id,
            )

        except FeishuApiError as exc:
            sync.sync_status = SyncStatus.FAILED.value
            sync.error_message = f"[{exc.code}] {exc.msg}"
            logger.error(
                "feishu_sync_failed",
                product_id=str(product.id),
                code=exc.code,
                msg=exc.msg,
            )

        except Exception as exc:
            sync.sync_status = SyncStatus.FAILED.value
            sync.error_message = str(exc)
            logger.error("feishu_sync_error", product_id=str(product.id), error=str(exc))

        await self._db.flush()
        return sync

    async def sync_all_pending(self) -> list[FeishuSyncRecord]:
        """Sync all products with AUTO_APPROVED status and no feishu_record_id.

        This can be called as a periodic task or after batch approvals.
        """
        from sqlalchemy import select

        result = await self._db.execute(
            select(Product).where(
                Product.review_status.in_(["auto_approved", "approved"]),
                Product.feishu_record_id.is_(None),
            )
        )
        products = list(result.scalars().all())
        records: list[FeishuSyncRecord] = []
        for product in products:
            try:
                record = await self.sync_product(product.id)
                records.append(record)
            except Exception as exc:
                logger.error("sync_all_error", product_id=str(product.id), error=str(exc))
        return records

    async def get_sync_status(self, product_id: uuid.UUID) -> list[FeishuSyncRecord]:
        """Get sync history for a product."""
        from sqlalchemy import select

        result = await self._db.execute(
            select(FeishuSyncRecord)
            .where(FeishuSyncRecord.product_id == product_id)
            .order_by(FeishuSyncRecord.created_at.desc())
            .limit(10),
        )
        return list(result.scalars().all())
