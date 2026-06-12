"""TaskEvent model — per-stage audit trail for a collection task."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
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
    stage: Mapped[TaskStage] = mapped_column(
        Enum(TaskStage, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationship
    task: Mapped["CollectionTask"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        stage_str = self.stage.value if isinstance(self.stage, TaskStage) else str(self.stage)
        status_str = self.status.value if isinstance(self.status, TaskStatus) else str(self.status)
        return f"<TaskEvent {stage_str} {status_str}>"
