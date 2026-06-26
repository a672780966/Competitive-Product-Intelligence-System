"""Discovery service — orchestrates source discovery flow.

Flow:
1. Check cache (SearchCacheService.get)
2. Search (SearchProvider.search)
3. Set cache (SearchCacheService.set)
4. LLM classify (LLMProvider.classify)
5. Build candidates with risk assessment + ranking
6. Record usage (UsageService.record_usage)
7. Record search history (SearchHistoryRepository.record)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import SourceCandidate, SourceDiscoverySession
from app.models.enums import DiscoveryStatus
from app.providers.interfaces import (
    LLMProvider,
    SearchProvider,
    SearchResult,
    assess_risk_level,
    rank_candidates,
    recommend_collector,
)
from app.providers.mock_providers import (
    MockSearchProvider,
    StubLLMProvider,
)
from app.repositories.discovery_repository import DiscoveryRepository
from app.repositories.search_history_repository import SearchHistoryRepository
from app.schemas.discovery import (
    CreateDiscoverySessionRequest,
    CreateTemplateFromSelectionRequest,
    CreateTemplateFromSelectionResponse,
    DiscoverySessionListResponse,
    DiscoverySessionResponse,
    PaginatedCandidateResponse,
    SessionDetailResponse,
    SourceCandidateResponse,
)
from app.services.search_cache_service import SearchCacheService
from app.services.usage_service import UsageService

logger = get_logger(__name__)


class DiscoveryService:
    """Business logic for source discovery orchestration."""

    def __init__(
        self,
        db: AsyncSession,
        search_provider: SearchProvider | None = None,
        llm_provider: LLMProvider | None = None,
        usage_service: UsageService | None = None,
        cache_service: SearchCacheService | None = None,
        search_history_repo: SearchHistoryRepository | None = None,
    ) -> None:
        self._db = db
        self._repo = DiscoveryRepository(db)
        # Default to mock providers — real ones can be injected
        self._search_provider = search_provider or MockSearchProvider()
        self._llm_provider = llm_provider or StubLLMProvider()
        self._usage_service = usage_service
        self._cache_service = cache_service or SearchCacheService()
        self._search_history_repo = search_history_repo or SearchHistoryRepository(db)

    # ── Session Lifecycle ───────────────────────────────────────

    async def create_session(
        self, req: CreateDiscoverySessionRequest,
    ) -> DiscoverySessionResponse:
        """Create a discovery session, run discovery, and return results."""
        # 1. Create session record
        session = SourceDiscoverySession(
            query=req.query,
            target_brand=req.target_brand,
            topic=req.topic,
            status=DiscoveryStatus.RUNNING,
            model_provider="llm",
            search_provider="mock",
        )
        session = await self._repo.create_session(session)
        logger.info(
            "discovery_session_created",
            session_id=str(session.id),
            query=req.query,
        )

        # 2. Run discovery
        candidates_created = 0
        try:
            candidates_created = await self._run_discovery(
                session, req.query, req.target_brand, req.topic,
            )
            updated = await self._repo.update_session_status(
                session.id, DiscoveryStatus.COMPLETED,
            )
            if updated is not None:
                session = updated
        except Exception as exc:
            logger.error(
                "discovery_failed",
                session_id=str(session.id),
                error=str(exc),
            )
            updated = await self._repo.update_session_status(
                session.id, DiscoveryStatus.FAILED,
                error_message=str(exc),
            )
            if updated is not None:
                session = updated

        # Reload session with candidates for accurate response
        session_with_candidates = await self._repo.get_session_with_candidates(
            session.id,
        )
        if session_with_candidates is not None:
            session = session_with_candidates

        resp = self._session_to_response(session)
        if session.candidates:
            resp.candidate_count = len(session.candidates)
        return resp

    async def get_session(
        self, session_id: uuid.UUID,
    ) -> SessionDetailResponse | None:
        """Get a session with its candidates."""
        session = await self._repo.get_session_with_candidates(session_id)
        if session is None:
            return None

        candidates = sorted(session.candidates, key=lambda c: c.sort_order)
        resp = self._session_to_response(session)
        resp.candidate_count = len(candidates)

        return SessionDetailResponse(
            session=resp,
            candidates=[self._candidate_to_response(c) for c in candidates],
        )

    async def list_sessions(
        self,
        *,
        status: DiscoveryStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DiscoverySessionListResponse:
        """List discovery sessions with pagination."""
        items, total = await self._repo.list_sessions(
            status=status, page=page, page_size=page_size,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)

        # Build response — count candidates via repository to avoid lazy loading
        result_items: list[DiscoverySessionResponse] = []
        for session in items:
            resp = self._session_to_response(session)
            # Get candidate count without lazy loading
            if session.id:
                _, candidate_total = await self._repo.list_candidates(
                    session.id, page=1, page_size=1,
                )
                resp.candidate_count = candidate_total
            result_items.append(resp)

        return DiscoverySessionListResponse(
            items=result_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ── Candidate Operations ────────────────────────────────────

    async def list_candidates(
        self,
        session_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedCandidateResponse | None:
        """List candidates for a session with pagination."""
        # Verify session exists
        session = await self._repo.get_session(session_id)
        if session is None:
            return None

        items, total = await self._repo.list_candidates(
            session_id, page=page, page_size=page_size,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)

        return PaginatedCandidateResponse(
            items=[self._candidate_to_response(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_candidate_selection(
        self, candidate_id: uuid.UUID, selected: bool,
    ) -> SourceCandidateResponse | None:
        """Update a candidate's selected flag."""
        candidate = await self._repo.update_candidate_selection(
            candidate_id, selected,
        )
        if candidate is None:
            return None
        return self._candidate_to_response(candidate)

    async def batch_select(
        self, session_id: uuid.UUID,
        candidate_ids: list[uuid.UUID],
        selected: bool,
    ) -> int:
        """Batch select/deselect candidates for a session."""
        # Verify session exists
        session = await self._repo.get_session(session_id)
        if session is None:
            return 0

        count = await self._repo.batch_update_selection(candidate_ids, selected)
        logger.info(
            "candidates_batch_selection",
            session_id=str(session_id),
            count=count,
            selected=selected,
        )
        return count

    # ── Template Creation ───────────────────────────────────────

    async def create_template_from_selection(
        self,
        session_id: uuid.UUID,
        req: CreateTemplateFromSelectionRequest,
    ) -> CreateTemplateFromSelectionResponse | None:
        """Create a CollectionTemplate from selected candidates."""
        from app.models import CollectionTemplate
        from app.models.enums import CollectionTemplateStatus

        # Get session with selected candidates
        session = await self._repo.get_session_with_candidates(session_id)
        if session is None:
            return None

        selected = await self._repo.get_selected_candidates(session_id)
        if not selected:
            logger.warning(
                "no_selected_candidates",
                session_id=str(session_id),
            )
            return CreateTemplateFromSelectionResponse(
                template_id=uuid.uuid4(),
                name=req.name,
                candidate_count=0,
                message="No selected candidates found — template created empty",
            )

        # Build source plan from selected candidates
        source_plan = {
            "query": session.query,
            "target_brand": session.target_brand,
            "topic": session.topic,
            "sources": [
                {
                    "title": c.title,
                    "url": c.url,
                    "domain": c.domain,
                    "source_type": c.source_type.value
                    if hasattr(c.source_type, "value") else c.source_type,
                    "recommended_collector": c.recommended_collector.value
                    if hasattr(c.recommended_collector, "value")
                    else c.recommended_collector,
                    "risk_level": c.risk_level.value
                    if hasattr(c.risk_level, "value") else c.risk_level,
                }
                for c in selected
            ],
        }

        run_plan = {
            "version": "1.0",
            "name": req.name,
            "sources": [
                {
                    "type": "url_list",
                    "urls": [c.url for c in selected],
                    "category_hint": session.topic,
                },
            ],
            "collector": {
                "kind": "direct_http",
                "params": {},
            },
            "scope": {
                "max_pages": 50,
                "max_pages_per_domain": 25,
                "respect_robots_txt": True,
                "delay_between_requests_ms": 500,
            },
        }

        template = CollectionTemplate(
            name=req.name,
            description=req.description,
            target_brand=session.target_brand,
            topic=session.topic,
            source_plan=source_plan,
            run_plan=run_plan,
            feishu_sync_enabled=req.feishu_sync_enabled,
            status=CollectionTemplateStatus.ACTIVE,
        )
        self._db.add(template)
        await self._db.flush()

        logger.info(
            "template_created_from_selection",
            template_id=str(template.id),
            session_id=str(session_id),
            candidate_count=len(selected),
        )

        return CreateTemplateFromSelectionResponse(
            template_id=template.id,
            name=template.name,
            candidate_count=len(selected),
            message=f"Template created with {len(selected)} sources",
        )

    # ── Internal ────────────────────────────────────────────────

    async def _run_discovery(
        self,
        session: SourceDiscoverySession,
        query: str,
        brand: str | None,
        topic: str | None,
    ) -> int:
        """Execute the discovery pipeline: cache → search → classify → persist.

        Returns the number of candidates created.
        """
        # 1. Check cache first
        cached_results = self._cache_service.get(
            query,
            brand=brand,
            topic=topic,
        )
        if cached_results is not None:
            logger.info(
                "discovery_cache_hit",
                session_id=str(session.id),
                query=query,
                count=len(cached_results),
            )
            raw_results: list[SearchResult] = cached_results
        else:
            # 2. Search
            raw_results = await self._search_provider.search(
                query, max_results=10, brand=brand, topic=topic,
            )
            # 3. Set cache
            self._cache_service.set(
                query, raw_results,
                brand=brand, topic=topic,
            )

        # 4. LLM classify each result
        candidates: list[SourceCandidate] = []
        for i, result in enumerate(raw_results):
            classified = await self._llm_provider.classify(
                title=result.title,
                snippet=result.snippet,
                url=result.url,
                brand=brand,
                topic=topic,
            )

            domain = self._extract_domain(result.url)
            risk_level = assess_risk_level(classified.source_type, domain)
            collector = recommend_collector(
                classified.source_type, risk_level, domain,
            )

            candidate = SourceCandidate(
                discovery_session_id=session.id,
                title=classified.suggested_title or result.title,
                url=result.url,
                domain=domain,
                snippet=result.snippet,
                source_type=classified.source_type,
                recommended_collector=collector,
                risk_level=risk_level,
                reason=classified.reason,
                selected=False,
                sort_order=i,
                raw_metadata={
                    "query": query,
                    "brand": brand,
                    "topic": topic,
                    "relevance_score": classified.relevance_score,
                    "confidence": classified.confidence,
                },
            )
            candidates.append(candidate)

        # 5. Rank candidates
        ranked_candidates = rank_candidates(
            candidates,
            boost_brand=brand,
            boost_topic=topic,
        )
        # Re-assign sort_order after ranking
        for i, c in enumerate(ranked_candidates):
            c.sort_order = i

        # 6. Persist candidates
        if ranked_candidates:
            await self._repo.bulk_create_candidates(ranked_candidates)
            logger.info(
                "discovery_candidates_created",
                session_id=str(session.id),
                count=len(ranked_candidates),
            )

        # 7. Record usage (if usage_service is wired)
        if self._usage_service is not None:
            try:
                await self._usage_service.record_usage(
                    search_count=1,
                )
            except Exception as exc:
                logger.warning(
                    "failed_to_record_usage",
                    session_id=str(session.id),
                    error=str(exc),
                )

        # 8. Record search history
        try:
            await self._search_history_repo.record(
                query=query,
                provider=self._search_provider.__class__.__name__,
                result_count=len(raw_results),
                brand=brand,
                topic=topic,
                session_id=session.id,
                raw_metadata={
                    "candidates_created": len(ranked_candidates),
                },
            )
        except Exception as exc:
            logger.warning(
                "failed_to_record_search_history",
                session_id=str(session.id),
                error=str(exc),
            )

        return len(ranked_candidates)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from a URL string."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc or parsed.path.split("/")[0]
        except Exception:
            return url

    # ── Mappers ─────────────────────────────────────────────────

    @staticmethod
    def _session_to_response(session: SourceDiscoverySession) -> DiscoverySessionResponse:
        status = session.status.value if hasattr(session.status, "value") else session.status
        return DiscoverySessionResponse(
            id=session.id,
            query=session.query,
            target_brand=session.target_brand,
            topic=session.topic,
            status=status if isinstance(status, str) else status,
            model_provider=session.model_provider,
            search_provider=session.search_provider,
            error_message=session.error_message,
            candidate_count=0,  # Callers should set this explicitly
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def _candidate_to_response(candidate: SourceCandidate) -> SourceCandidateResponse:
        def _val(obj: Any) -> str:
            return obj.value if hasattr(obj, "value") else (str(obj) if obj else "")

        return SourceCandidateResponse(
            id=candidate.id,
            discovery_session_id=candidate.discovery_session_id,
            title=candidate.title,
            url=candidate.url,
            domain=candidate.domain,
            snippet=candidate.snippet,
            thumbnail_url=candidate.thumbnail_url,
            favicon_url=candidate.favicon_url,
            source_type=_val(candidate.source_type),
            recommended_collector=_val(candidate.recommended_collector),
            risk_level=_val(candidate.risk_level),
            reason=candidate.reason,
            selected=candidate.selected,
            raw_metadata=candidate.raw_metadata,
            sort_order=candidate.sort_order,
            created_at=candidate.created_at,
        )
