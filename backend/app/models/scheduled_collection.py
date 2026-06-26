"""ScheduledCollection model — recurring schedule tied to a collection template."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ScheduleType
from app.models.types import GUID


class ScheduledCollection(Base, TimestampMixin):
    __tablename__ = "scheduled_collections"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("collection_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    schedule_type: Mapped[ScheduleType] = mapped_column(
        String(16), nullable=False, default=ScheduleType.DAILY,
    )
    cron_expr: Mapped[str | None] = mapped_column(String(128))
    interval_minutes: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(32))
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_failures_before_pause: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False,
    )

    # relationships
    template: Mapped["CollectionTemplate"] = relationship(back_populates="schedules")

    def __repr__(self) -> str:
        return f"<ScheduledCollection {self.id} template={self.template_id}>"
