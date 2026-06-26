"""CPIS V1 — SQLAlchemy models.

All models inherit from ``Base`` (declarative base).
Import here so Alembic's ``env.py`` can discover them via ``from app.models import Base``.
"""

from __future__ import annotations

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    CollectionTemplateStatus,
    DiscoveryStatus,
    ProductCategory,
    RecommendedCollector,
    ReviewStatus,
    RiskLevel,
    ScheduleType,
    SourceType,
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

from app.models.source_discovery_session import SourceDiscoverySession
from app.models.source_candidate import SourceCandidate
from app.models.collection_template import CollectionTemplate
from app.models.scheduled_collection import ScheduledCollection
from app.models.usage_daily_stat import UsageDailyStat
from app.models.search_history import SearchHistory
from app.models.collector_execution_report import CollectorExecutionReport

__all__ = [
    "Base",
    "TimestampMixin",
    "CollectionTemplateStatus",
    "DiscoveryStatus",
    "ProductCategory",
    "RecommendedCollector",
    "ReviewStatus",
    "RiskLevel",
    "ScheduleType",
    "SourceType",
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
    "SourceDiscoverySession",
    "SourceCandidate",
    "CollectionTemplate",
    "ScheduledCollection",
    "UsageDailyStat",
    "SearchHistory",
    "CollectorExecutionReport",
]
