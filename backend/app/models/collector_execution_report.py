"""CollectorExecutionReport model — records the result of a collector execution."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GUID


class CollectorExecutionReport(Base, TimestampMixin):
    __tablename__ = "collector_execution_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("collection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("source_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    collector_runtime: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="started", index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CollectorExecutionReport {self.id} "
            f"task={self.task_id} "
            f"collector={self.collector_runtime} "
            f"status={self.status}>"
        )
