"""Align review_records and collection_tasks with models.
-
Fixes 3 mismatches:
1. collection_tasks.auto_sync_feishu — add missing boolean column
2. review_records.corrections — alter String→JSONB
3. review_records.changed_fields — add missing JSONB column

Revision ID: 002_align_fields
Revises: 001_initial_schema
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_align_fields"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add missing auto_sync_feishu to collection_tasks
    op.add_column(
        "collection_tasks",
        sa.Column("auto_sync_feishu", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 2. Alter corrections from String(2048) to JSONB
    op.alter_column(
        "review_records",
        "corrections",
        type_=postgresql.JSONB(),
        postgresql_using="corrections::jsonb",
    )

    # 3. Add missing changed_fields to review_records
    op.add_column(
        "review_records",
        sa.Column("changed_fields", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    # Reverse order of upgrade
    op.drop_column("review_records", "changed_fields")

    op.alter_column(
        "review_records",
        "corrections",
        type_=sa.String(2048),
        postgresql_using="corrections::varchar",
    )

    op.drop_column("collection_tasks", "auto_sync_feishu")
