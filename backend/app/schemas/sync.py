"""CPIS V1 - Sync record schemas for API responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.models.enums import SyncStatus


class SyncRecordResponse(BaseModel):
    """Sync record detail."""

    id: uuid.UUID
    product_id: uuid.UUID
    sync_status: str
    sync_type: str
    feishu_record_id: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    synced_at: datetime | None

    @field_serializer("sync_status")
    def serialize_sync_status(self, value: str | SyncStatus) -> str:
        """Return enum-backed values as plain status strings."""
        if isinstance(value, SyncStatus):
            return value.value
        return value

    model_config = {"from_attributes": True}


class PaginatedSyncResponse(BaseModel):
    """Paginated list of sync records."""

    items: list[SyncRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
