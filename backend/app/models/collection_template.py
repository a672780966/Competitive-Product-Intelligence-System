"""CollectionTemplate model — named template for a declarative collection run."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CollectionTemplateStatus
from app.models.types import GUID, JSONB


class CollectionTemplate(Base, TimestampMixin):
    __tablename__ = "collection_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    target_brand: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(255))
    source_plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    run_plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    feishu_sync_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    status: Mapped[CollectionTemplateStatus] = mapped_column(
        String(16), default=CollectionTemplateStatus.ACTIVE,
        index=True, nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # relationships
    schedules: Mapped[list["ScheduledCollection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CollectionTemplate {self.id} {self.name}>"
