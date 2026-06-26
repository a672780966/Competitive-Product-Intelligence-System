"""CPIS V1 — Enum definitions for all database models."""

from __future__ import annotations

import enum


class TaskStatus(str, enum.Enum):
    """Collection task lifecycle status — matches the state machine defined in Node 05."""

    PENDING = "pending"
    VALIDATING = "validating"
    FETCHING = "fetching"
    CLEANING = "cleaning"
    EXTRACTING = "extracting"
    REVIEW_PENDING = "review_pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(int, enum.Enum):
    """Task priority levels."""

    LOW = 10
    NORMAL = 50
    HIGH = 100
    URGENT = 200


class ReviewStatus(str, enum.Enum):
    """Product review lifecycle status."""

    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    NEEDS_REVIEW = "needs_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REOPENED = "reopened"


class ProductCategory(str, enum.Enum):
    """High-level product categories."""

    SMARTPHONE = "smartphone"
    LAPTOP = "laptop"
    TABLET = "tablet"
    WEARABLE = "wearable"
    AUDIO = "audio"
    ACCESSORY = "accessory"
    SMART_HOME = "smart_home"
    OTHER = "other"


class SyncStatus(str, enum.Enum):
    """Feishu sync record status."""

    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


class TaskStage(str, enum.Enum):
    """Stages within a collection task pipeline."""

    VALIDATION = "validation"
    COLLECTION = "collection"
    CLEANING = "cleaning"
    EXTRACTION = "extraction"
    REVIEW = "review"
    SYNC = "sync"
    REPORT = "report"


class DiscoveryStatus(str, enum.Enum):
    """Lifecycle status for a source discovery session."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, enum.Enum):
    """Classification of a discovered source URL."""

    OFFICIAL_HOMEPAGE = "official_homepage"
    PRODUCT_DETAIL = "product_detail"
    DOCUMENTATION = "documentation"
    NEWS = "news"
    REVIEW = "review"
    FORUM = "forum"
    SOCIAL = "social"
    OTHER = "other"


class RecommendedCollector(str, enum.Enum):
    """Recommended collector kind for a source candidate."""

    DIRECT_HTTP = "direct_http"
    PLAYWRIGHT = "playwright"
    SCRAPLING_FEATURE_FLAG = "scrapling_feature_flag"
    CRAWL4AI_FEATURE_FLAG = "crawl4ai_feature_flag"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class RiskLevel(str, enum.Enum):
    """Risk classification for a source candidate."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class CollectionTemplateStatus(str, enum.Enum):
    """Lifecycle status for a collection template."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ScheduleType(str, enum.Enum):
    """Type of schedule for a scheduled collection."""

    CRON = "cron"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
