"""PromptTemplate model — versioned LLM system prompts."""

from __future__ import annotations

import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GUID


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    model: Mapped[str | None] = mapped_column(String(64))

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name} v{self.version}>"
