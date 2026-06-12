"""TaskEvent model — per-stage audit trail for a collection task."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TaskStage, TaskStatus
from app.models.types import GUID


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("collection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    stage: Mapped[TaskStage] = mapped_column(String(32), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationship
    task: Mapped["CollectionTask"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<TaskEvent {self.stage} {self.status.value}>"
