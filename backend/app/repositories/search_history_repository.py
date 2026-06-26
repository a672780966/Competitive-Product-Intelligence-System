"""Search history repository — CRUD for SearchHistory model.

Records past search queries with metadata for audit, usage tracking,
and cache invalidation strategies.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_history import SearchHistory


class SearchHistoryRepository:
    """Data access for SearchHistory records.

    Usage:
        repo = SearchHistoryRepository(db)
        record = await repo.record(query="xiaomi 14 ultra", provider="duckduckgo", result_count=8)
        history = await repo.list_history(limit=20)
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        query: str,
        provider: str,
        result_count: int,
        *,
        brand: str | None = None,
        topic: str | None = None,
        session_id: uuid.UUID | None = None,
        raw_metadata: dict[str, Any] | None = None,
    ) -> SearchHistory:
        """Record a search query in history.

        Args:
            query: The search query string.
            provider: Name of the search provider used.
            result_count: Number of results returned.
            brand: Optional brand context.
            topic: Optional topic context.
            session_id: Optional discovery session ID for traceability.
            raw_metadata: Optional extra metadata dict.

        Returns:
            The persisted SearchHistory record.
        """
        record = SearchHistory(
            query=query,
            provider=provider,
            result_count=result_count,
            brand=brand,
            topic=topic,
            session_id=session_id,
            raw_metadata=json.dumps(raw_metadata) if raw_metadata else None,
        )
        self._db.add(record)
        await self._db.flush()
        return record

    async def list_history(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """List recent search history entries, newest first.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).

        Returns:
            List of SearchHistory records, ordered by created_at desc.
        """
        result = await self._db.execute(
            select(SearchHistory)
            .order_by(SearchHistory.created_at.desc(), SearchHistory.id.desc())
            .offset(offset)
            .limit(limit),
        )
        return list(result.scalars().all())

    async def get_by_session(
        self,
        session_id: uuid.UUID,
    ) -> SearchHistory | None:
        """Get the search history record for a specific discovery session.

        Args:
            session_id: The discovery session UUID.

        Returns:
            The matching SearchHistory record, or None.
        """
        result = await self._db.execute(
            select(SearchHistory).where(
                SearchHistory.session_id == session_id,
            ),
        )
        return result.scalar_one_or_none()

    async def count_by_query(
        self,
        query: str,
        *,
        provider: str | None = None,
    ) -> int:
        """Count how many times a query has been searched.

        Args:
            query: The search query string.
            provider: Optional provider filter.

        Returns:
            Total count of matching records.
        """
        stmt = select(func.count(SearchHistory.id)).where(
            SearchHistory.query == query,
        )
        if provider is not None:
            stmt = stmt.where(SearchHistory.provider == provider)
        result = await self._db.execute(stmt)
        return result.scalar() or 0
