"""SearchHistory model — records of past search queries with metadata.

Used for audit, usage tracking, and cache invalidation strategies.
Linked to discovery sessions for traceability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import GUID


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16))
    brand: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(255))
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("discovery_sessions.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    raw_metadata: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SearchHistory {self.id} query={self.query!r}>"
