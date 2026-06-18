"""Product model — master product record deduplicated by unique_key."""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProductCategory, ReviewStatus
from app.models.types import GUID


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    unique_key: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False, index=True,
    )
    brand: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(512))
    model: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[ProductCategory | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(2048))

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, nullable=True,
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        String(32), default=ReviewStatus.PENDING, nullable=False, index=True,
    )
    feishu_record_id: Mapped[str | None] = mapped_column(
        String(128), index=True,
    )

    # relationships
    versions: Mapped[list[ProductVersion]] = relationship(
        back_populates="product", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Product {self.unique_key}>"
