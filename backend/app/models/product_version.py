"""ProductVersion model — one version (snapshot in time) of a product."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import GUID, JSONB


class ProductVersion(Base):
    __tablename__ = "product_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)

    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("source_snapshots.id", ondelete="SET NULL"),
    )
    structured_data: Mapped[dict | None] = mapped_column(JSONB)
    analysis_data: Mapped[dict | None] = mapped_column(JSONB)

    ai_model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    overall_confidence: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    product: Mapped["Product"] = relationship(back_populates="versions")
    evidences: Mapped[list["ProductEvidence"]] = relationship(
        back_populates="product_version", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProductVersion {self.product_id} v{self.version_no}>"
