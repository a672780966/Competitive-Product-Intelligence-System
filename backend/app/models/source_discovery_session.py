"""SourceDiscoverySession model — tracks one discovery query session."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DiscoveryStatus
from app.models.types import GUID


class SourceDiscoverySession(Base, TimestampMixin):
    __tablename__ = "discovery_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    target_brand: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[DiscoveryStatus] = mapped_column(
        String(32), default=DiscoveryStatus.CREATED, index=True, nullable=False,
    )
    model_provider: Mapped[str | None] = mapped_column(String(64))
    search_provider: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    # relationships
    candidates: Mapped[list["SourceCandidate"]] = relationship(
        back_populates="discovery_session", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        status = self.status.value if hasattr(self.status, "value") else self.status
        return f"<SourceDiscoverySession {self.id} {status}>"
