"""CollectionTask model — tracks the lifecycle of one URL collection job."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import TaskPriority, TaskStatus
from app.models.types import GUID


class CollectionTask(Base, TimestampMixin):
    __tablename__ = "collection_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    normalized_url: Mapped[str | None] = mapped_column(String(2048))
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=TaskStatus.PENDING, index=True, nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Integer, default=TaskPriority.NORMAL, nullable=False,
    )
    category_hint: Mapped[str | None] = mapped_column(String(64))
    language_hint: Mapped[str | None] = mapped_column(String(16))
    auto_sync_feishu: Mapped[bool] = mapped_column(default=False, nullable=False)

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # relationships
    events: Mapped[list[TaskEvent]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )
    snapshot: Mapped[SourceSnapshot | None] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False,
    )

    def __repr__(self) -> str:
        status_str = self.status.value if isinstance(self.status, TaskStatus) else str(self.status)
        return f"<CollectionTask {self.id} {status_str}>"
