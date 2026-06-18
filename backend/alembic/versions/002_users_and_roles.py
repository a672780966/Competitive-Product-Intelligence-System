"""Add users, roles, user_roles tables

Revision ID: 002_users_and_roles
Revises: 001_initial_schema
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002_users_and_roles"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("description", sa.String(255)),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
    )

    # Seed default roles
    op.execute(
        """
        INSERT INTO roles (name, description) VALUES
        ('admin', 'System administrator'),
        ('operator', 'Can create tasks and review'),
        ('viewer', 'Read-only access'),
        ('auditor', 'Can view audit logs')
        """,
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
