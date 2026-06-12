"""CPIS V1 — Enum definitions for all database models."""

from __future__ import annotations

import enum


class TaskStatus(str, enum.Enum):
    """Collection task lifecycle status."""

    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    COLLECTING = "collecting"
    COLLECTED = "collected"
    CLEANING = "cleaning"
    CLEANED = "cleaned"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
