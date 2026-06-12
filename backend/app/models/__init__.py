"""CPIS V1 — SQLAlchemy models.

All models inherit from ``Base`` (declarative base).
Import here so Alembic's ``env.py`` can discover them via ``from app.models import Base``.
"""

from __future__ import annotations

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    ProductCategory,
    ReviewStatus,
    SyncStatus,
    TaskPriority,
    TaskStage,
    TaskStatus,
)
from app.models.collection_task import CollectionTask
from app.models.task_event import TaskEvent
from app.models.source_snapshot import SourceSnapshot
from app.models.product import Product
from app.models.product_version import ProductVersion
from app.models.product_evidence import ProductEvidence
from app.models.review_record import ReviewRecord
from app.models.feishu_sync_record import FeishuSyncRecord
from app.models.prompt_template import PromptTemplate
from app.models.audit_log import AuditLog

__all__ = [
    "Base",
    "TimestampMixin",
    "ProductCategory",
    "ReviewStatus",
    "SyncStatus",
    "TaskPriority",
    "TaskStage",
    "TaskStatus",
    "CollectionTask",
    "TaskEvent",
    "SourceSnapshot",
    "Product",
    "ProductVersion",
    "ProductEvidence",
    "ReviewRecord",
    "FeishuSyncRecord",
    "PromptTemplate",
    "AuditLog",
]
