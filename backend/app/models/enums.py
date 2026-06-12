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
