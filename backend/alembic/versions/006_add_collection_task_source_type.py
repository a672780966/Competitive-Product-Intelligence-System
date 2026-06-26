"""006_add_collection_task_source_type

Add source_type column to collection_tasks.

Revision ID: 006_add_source_type
Revises: 005_add_exec_reports
Create Date: 2026-06-26 13:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_add_source_type"
down_revision: Union[str, None] = "005_add_exec_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collection_tasks",
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=True,
            server_default=sa.text("'other'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("collection_tasks", "source_type")
