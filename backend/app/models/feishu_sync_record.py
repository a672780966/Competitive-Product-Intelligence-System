"""FeishuSyncRecord model — tracks each sync to Feishu Bitable."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import SyncStatus
from app.models.types import GUID


class FeishuSyncRecord(Base):
    __tablename__ = "feishu_sync_records"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        String(32), default=SyncStatus.PENDING, nullable=False,
    )
    sync_type: Mapped[str] = mapped_column(String(32), default="bitable", nullable=False)
    feishu_record_id: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<FeishuSyncRecord {self.id} {self.sync_status.value}>"
