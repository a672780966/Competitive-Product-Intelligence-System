"""User, Role, and UserRole models for RBAC."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.types import GUID


class Role(Base):
    """Pre-defined roles: admin, operator, viewer, auditor."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class User(Base, TimestampMixin):
    """Application user with role-based access control."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
    )
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )

    # Many-to-many relationship via user_roles
    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="user_roles", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class UserRole(Base):
    """Junction table linking users to roles."""

    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False,
    )
