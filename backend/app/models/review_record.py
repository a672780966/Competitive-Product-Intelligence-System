"""ReviewRecord model — human review trail for one product version."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ReviewStatus
from app.models.types import GUID, JSONB


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
    decision: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text)
    corrections: Mapped[dict | None] = mapped_column(JSONB)
    changed_fields: Mapped[list | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        decision_str = self.decision.value if isinstance(self.decision, ReviewStatus) else str(self.decision)
        return f"<ReviewRecord {self.id} {decision_str}>"
