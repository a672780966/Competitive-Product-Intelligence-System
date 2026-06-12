"""CPIS V1 — 初始数据库表结构

创建核心 10 张表：

- collection_tasks
- task_events
- source_snapshots
- products
- product_versions
- product_evidences
- review_records
- feishu_sync_records
- prompt_templates
- audit_logs

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-06-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- collection_tasks ---
    op.create_table(
        "collection_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_url", sa.String(2048), nullable=False, index=True),
        sa.Column("normalized_url", sa.String(2048), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("category_hint", sa.String(64), nullable=True),
        sa.Column("language_hint", sa.String(16), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- task_events ---
    op.create_table(
        "task_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("collection_tasks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- source_snapshots ---
    op.create_table(
        "source_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("collection_tasks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("final_url", sa.String(2048), nullable=True),
        sa.Column("html_hash", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("raw_html", sa.LargeBinary(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("cleaned_markdown", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("unique_key", sa.String(512), unique=True, nullable=False, index=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_status", sa.String(32), nullable=False, index=True, server_default="pending"),
        sa.Column("feishu_record_id", sa.String(128), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- product_versions ---
    op.create_table(
        "product_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("structured_data", postgresql.JSONB(), nullable=True),
        sa.Column("analysis_data", postgresql.JSONB(), nullable=True),
        sa.Column("ai_model", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- product_evidences ---
    op.create_table(
        "product_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field_name", sa.String(128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("evidence_source", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- review_records ---
    op.create_table(
        "review_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("reviewer", sa.String(128), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("corrections", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- feishu_sync_records ---
    op.create_table(
        "feishu_sync_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("sync_type", sa.String(32), nullable=False, server_default="bitable"),
        sa.Column("feishu_record_id", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- prompt_templates ---
    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor", sa.String(128), nullable=True, index=True),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("audit_logs")
    op.drop_table("prompt_templates")
    op.drop_table("feishu_sync_records")
    op.drop_table("review_records")
    op.drop_table("product_evidences")
    op.drop_table("product_versions")
    op.drop_table("products")
    op.drop_table("source_snapshots")
    op.drop_table("task_events")
    op.drop_table("collection_tasks")
