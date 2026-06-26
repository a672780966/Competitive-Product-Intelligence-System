"""Repository for SourceDiscoverySession and SourceCandidate models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import SourceCandidate, SourceDiscoverySession
from app.models.enums import DiscoveryStatus


class DiscoveryRepository:
    """Data access for SourceDiscoverySession and SourceCandidate."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Discovery Session ───────────────────────────────────────

    async def create_session(
        self, session: SourceDiscoverySession,
    ) -> SourceDiscoverySession:
        """Persist a new discovery session."""
        self._db.add(session)
        await self._db.flush()
        return session

    async def get_session(
        self, session_id: uuid.UUID,
    ) -> SourceDiscoverySession | None:
        """Get a session by ID."""
        result = await self._db.execute(
            select(SourceDiscoverySession).where(
                SourceDiscoverySession.id == session_id,
            ),
        )
        return result.scalar_one_or_none()

    async def get_session_with_candidates(
        self, session_id: uuid.UUID,
    ) -> SourceDiscoverySession | None:
        """Get a session with its candidates eagerly loaded."""
        result = await self._db.execute(
            select(SourceDiscoverySession)
            .where(SourceDiscoverySession.id == session_id)
            .options(selectinload(SourceDiscoverySession.candidates)),
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        *,
        status: DiscoveryStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SourceDiscoverySession], int]:
        """List sessions with optional status filter, returns (items, total)."""
        query = select(SourceDiscoverySession)
        count_query = select(func.count(SourceDiscoverySession.id))

        if status:
            query = query.where(SourceDiscoverySession.status == status.value)
            count_query = count_query.where(
                SourceDiscoverySession.status == status.value,
            )

        # Count total
        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        # Order + paginate
        query = (
            query
            .order_by(SourceDiscoverySession.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_session_status(
        self,
        session_id: uuid.UUID,
        status: DiscoveryStatus,
        error_message: str | None = None,
    ) -> SourceDiscoverySession | None:
        """Update session status."""
        values: dict = {"status": status.value}
        if error_message:
            values["error_message"] = error_message

        stmt = (
            update(SourceDiscoverySession)
            .where(SourceDiscoverySession.id == session_id)
            .values(**values)
        )
        await self._db.execute(stmt)
        return await self.get_session(session_id)

    # ── Source Candidate ────────────────────────────────────────

    async def create_candidate(
        self, candidate: SourceCandidate,
    ) -> SourceCandidate:
        """Persist a new candidate."""
        self._db.add(candidate)
        await self._db.flush()
        return candidate

    async def bulk_create_candidates(
        self, candidates: list[SourceCandidate],
    ) -> list[SourceCandidate]:
        """Persist multiple candidates at once."""
        for c in candidates:
            self._db.add(c)
        await self._db.flush()
        return candidates

    async def get_candidate(
        self, candidate_id: uuid.UUID,
    ) -> SourceCandidate | None:
        """Get a candidate by ID."""
        result = await self._db.execute(
            select(SourceCandidate).where(
                SourceCandidate.id == candidate_id,
            ),
        )
        return result.scalar_one_or_none()

    async def list_candidates(
        self,
        session_id: uuid.UUID | None = None,
        *,
        selected: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SourceCandidate], int]:
        """List candidates with optional filters, returns (items, total)."""
        query = select(SourceCandidate)
        count_query = select(func.count(SourceCandidate.id))

        if session_id:
            query = query.where(
                SourceCandidate.discovery_session_id == session_id,
            )
            count_query = count_query.where(
                SourceCandidate.discovery_session_id == session_id,
            )
        if selected is not None:
            query = query.where(SourceCandidate.selected == selected)
            count_query = count_query.where(SourceCandidate.selected == selected)

        # Count total
        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        # Order + paginate
        query = (
            query
            .order_by(SourceCandidate.sort_order.asc(), SourceCandidate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_candidate_selection(
        self,
        candidate_id: uuid.UUID,
        selected: bool,
    ) -> SourceCandidate | None:
        """Update a candidate's selected flag."""
        stmt = (
            update(SourceCandidate)
            .where(SourceCandidate.id == candidate_id)
            .values(selected=selected)
        )
        await self._db.execute(stmt)
        return await self.get_candidate(candidate_id)

    async def batch_update_selection(
        self,
        candidate_ids: list[uuid.UUID],
        selected: bool,
    ) -> int:
        """Update selected flag for multiple candidates. Returns count updated."""
        stmt = (
            update(SourceCandidate)
            .where(SourceCandidate.id.in_(candidate_ids))
            .values(selected=selected)
        )
        result = await self._db.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_selected_candidates(
        self, session_id: uuid.UUID,
    ) -> list[SourceCandidate]:
        """Get all selected candidates for a session."""
        result = await self._db.execute(
            select(SourceCandidate)
            .where(
                SourceCandidate.discovery_session_id == session_id,
                SourceCandidate.selected == True,  # noqa: E712
            )
            .order_by(SourceCandidate.sort_order.asc()),
        )
        return list(result.scalars().all())
