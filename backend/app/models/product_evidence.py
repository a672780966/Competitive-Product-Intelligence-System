"""ProductEvidence model — per-field evidence for AI extraction provenance."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import GUID


class ProductEvidence(Base):
    __tablename__ = "product_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("product_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    evidence_source: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    product_version: Mapped["ProductVersion"] = relationship(back_populates="evidences")

    def __repr__(self) -> str:
        return f"<ProductEvidence {self.field_name}={self.value}>"
