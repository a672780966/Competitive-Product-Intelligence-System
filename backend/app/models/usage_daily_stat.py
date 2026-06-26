"""UsageDailyStat model — daily aggregated usage statistics."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GUID, JSONB


class UsageDailyStat(Base, TimestampMixin):
    __tablename__ = "usage_daily_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    stat_date: Mapped[date] = mapped_column(
        Date, unique=True, nullable=False, index=True,
    )
    task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collected_page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<UsageDailyStat {self.stat_date}>"
