"""SourceCandidate model — a discovered source URL from a discovery session."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RecommendedCollector, RiskLevel, SourceType
from app.models.types import GUID, JSONB


class SourceCandidate(Base):
    __tablename__ = "source_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    discovery_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("discovery_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    snippet: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048))
    favicon_url: Mapped[str | None] = mapped_column(String(2048))
    source_type: Mapped[SourceType] = mapped_column(
        String(32), nullable=False, default=SourceType.OTHER,
    )
    recommended_collector: Mapped[RecommendedCollector] = mapped_column(
        String(32), nullable=False, default=RecommendedCollector.DIRECT_HTTP,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        String(16), nullable=False, default=RiskLevel.LOW,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    discovery_session: Mapped["SourceDiscoverySession"] = relationship(
        back_populates="candidates",
    )

    def __repr__(self) -> str:
        return f"<SourceCandidate {self.id} {self.domain}>"
