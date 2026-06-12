"""SourceSnapshot model — raw and cleaned content of a fetched page."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import GUID


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("collection_tasks.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    final_url: Mapped[str | None] = mapped_column(String(2048))
    html_hash: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_html: Mapped[bytes | None] = mapped_column(LargeBinary)
    cleaned_text: Mapped[str | None] = mapped_column(Text)
    cleaned_markdown: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    task: Mapped[CollectionTask] = relationship(back_populates="snapshot")

    def __repr__(self) -> str:
        return f"<SourceSnapshot {self.id} task={self.task_id}>"
