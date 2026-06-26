"""005_add_collector_execution_reports

Add collector_execution_reports table and risk_level column to collection_tasks.

Revision ID: 005_add_exec_reports
Revises: 004_add_search_history
Create Date: 2026-06-26 12:45:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "005_add_exec_reports"
down_revision: Union[str, None] = "004_add_search_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── collector_execution_reports table ─────────────────────
    op.create_table(
        "collector_execution_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("collector_runtime", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'started'"),
            index=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("content_size", sa.Integer(), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default=sa.text("0"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["collection_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["source_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collector_execution_reports_task_id"),
        "collector_execution_reports",
        ["task_id"],
        unique=False,
    )

    # ── risk_level column on collection_tasks ─────────────────
    op.add_column(
        "collection_tasks",
        sa.Column(
            "risk_level",
            sa.String(length=16),
            nullable=True,
            server_default=sa.text("'low'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("collection_tasks", "risk_level")
    op.drop_index(
        op.f("ix_collector_execution_reports_task_id"),
        table_name="collector_execution_reports",
    )
    op.drop_table("collector_execution_reports")
