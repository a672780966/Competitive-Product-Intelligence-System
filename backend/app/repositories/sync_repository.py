"""CPIS V1 - Sync record repository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeishuSyncRecord


class SyncRepository:
    """Read-only data access for Feishu sync records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, record_id: uuid.UUID) -> FeishuSyncRecord | None:
        """Get a sync record by primary key."""
        result = await self._db.execute(
            select(FeishuSyncRecord).where(FeishuSyncRecord.id == record_id),
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: str | None = None,
        product_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FeishuSyncRecord], int]:
        """List sync records with optional filters, returns (items, total_count)."""
        query = select(FeishuSyncRecord)
        count_query = select(func.count(FeishuSyncRecord.id))

        conditions = []
        if status:
            conditions.append(FeishuSyncRecord.sync_status == status)
        if product_id:
            conditions.append(FeishuSyncRecord.product_id == product_id)

        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        query = (
            query
            .order_by(FeishuSyncRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        return list(result.scalars().all()), total
