"""ReviewRecord model — human review trail for one product version."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ReviewStatus
from app.models.types import GUID


class ReviewRecord(Base, TimestampMixin):
    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("product_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reviewer: Mapped[str | None] = mapped_column(String(128))
    decision: Mapped[ReviewStatus] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    corrections: Mapped[dict | None] = mapped_column(String(2048))
    # corrections stored as JSON string — parsed by service layer

    def __repr__(self) -> str:
        return f"<ReviewRecord {self.id} {self.decision.value}>"
