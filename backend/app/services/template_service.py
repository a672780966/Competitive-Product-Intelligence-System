"""TemplateService — CRUD and run operations for CollectionTemplate.

Handles:
- Listing, getting, updating templates
- Running a template (creating tasks from source_plan)
- RunPlan validation
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import CollectionTemplate
from app.models.enums import CollectionTemplateStatus
from app.schemas.run_plan import validate_run_plan
from app.schemas.template_schedule import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateRunResponse,
    TemplateUpdateRequest,
)
from app.services.collection_runner_service import RunPlanExecutor

logger = get_logger(__name__)


class TemplateService:
    """Business logic for collection template management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Query ────────────────────────────────────────────────────

    async def list_templates(
        self,
        *,
        status: CollectionTemplateStatus | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TemplateListResponse:
        """List templates with optional filters and pagination."""
        query = select(CollectionTemplate)
        count_query = select(func.count(CollectionTemplate.id))

        if status:
            query = query.where(CollectionTemplate.status == status.value)
            count_query = count_query.where(CollectionTemplate.status == status.value)
        if search:
            pattern = f"%{search}%"
            query = query.where(CollectionTemplate.name.ilike(pattern))
            count_query = count_query.where(CollectionTemplate.name.ilike(pattern))

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        query = (
            query
            .order_by(CollectionTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())

        total_pages = max(1, (total + page_size - 1) // page_size)

        return TemplateListResponse(
            items=[self._to_response(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_template(
        self, template_id: uuid.UUID,
    ) -> TemplateResponse | None:
        """Get a template by ID."""
        result = await self._db.execute(
            select(CollectionTemplate).where(CollectionTemplate.id == template_id),
        )
        template = result.scalar_one_or_none()
        if template is None:
            return None
        return self._to_response(template)

    async def update_template(
        self,
        template_id: uuid.UUID,
        req: TemplateUpdateRequest,
    ) -> TemplateResponse | None:
        """Update a template's name, description, or status."""
        values: dict[str, Any] = {}
        if req.name is not None:
            values["name"] = req.name
        if req.description is not None:
            values["description"] = req.description
        if req.status is not None:
            values["status"] = req.status.value if hasattr(req.status, "value") else req.status

        if values:
            stmt = (
                update(CollectionTemplate)
                .where(CollectionTemplate.id == template_id)
                .values(**values)
            )
            await self._db.execute(stmt)

        return await self.get_template(template_id)

    # ── Run ──────────────────────────────────────────────────────

    async def run_template(
        self,
        template_id: uuid.UUID,
        *,
        created_by: str = "system",
    ) -> TemplateRunResponse | None:
        """Execute a template: create tasks from its source_plan.

        Uses RunPlanExecutor to create CollectionTasks from the template's
        source_plan/run_plan.
        """
        result = await self._db.execute(
            select(CollectionTemplate).where(CollectionTemplate.id == template_id),
        )
        template = result.scalar_one_or_none()
        if template is None:
            return None

        # Use the run_plan if available and valid, otherwise build from source_plan
        plan_data = template.run_plan
        if plan_data:
            try:
                validate_run_plan(plan_data)
            except Exception:
                logger.warning(
                    "run_plan_validation_failed_falling_back_to_source_plan",
                    template_id=str(template_id),
                )
                plan_data = self._build_plan_from_source_plan(template)
        else:
            plan_data = self._build_plan_from_source_plan(template)

        executor = RunPlanExecutor(self._db)
        tasks = await executor.execute_plan(
            plan_data,
            created_by=created_by,
        )

        logger.info(
            "template_executed",
            template_id=str(template_id),
            task_count=len(tasks),
        )

        return TemplateRunResponse(
            template_id=template_id,
            tasks_created=len(tasks),
            message=f"Template executed: {len(tasks)} tasks created",
        )

    # ── Create ───────────────────────────────────────────────────

    async def create_template(self, req: TemplateCreateRequest) -> TemplateResponse:
        """Create a collection template from simple demo sources."""
        urls = [src.url for src in req.sources]
        source_plan = {"sources": [src.model_dump() for src in req.sources]}
        run_plan = {
            "version": "1.0",
            "name": req.name,
            "sources": [
                {
                    "type": "url_list",
                    "urls": urls,
                    "category_hint": req.topic or req.sources[0].category_hint,
                }
            ],
        }
        validate_run_plan(run_plan)
        template = CollectionTemplate(
            name=req.name,
            description=req.description,
            target_brand=req.target_brand,
            topic=req.topic,
            source_plan=source_plan,
            run_plan=run_plan,
            feishu_sync_enabled=req.feishu_sync_enabled,
            status=CollectionTemplateStatus.ACTIVE.value,
        )
        self._db.add(template)
        await self._db.flush()
        await self._db.refresh(template)
        return self._to_response(template)

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _to_response(template: CollectionTemplate) -> TemplateResponse:
        """Map a CollectionTemplate ORM model to a response schema."""
        status = template.status
        if hasattr(status, "value"):
            status = status.value
        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            target_brand=template.target_brand,
            topic=template.topic,
            source_plan=template.source_plan or {},
            run_plan=template.run_plan or {},
            feishu_sync_enabled=template.feishu_sync_enabled,
            status=status,
            last_run_at=template.last_run_at,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    @staticmethod
    def _build_plan_from_source_plan(template: CollectionTemplate) -> dict:
        """Build a RunPlan from a template's source_plan.

        Used when the template was created from a discovery session
        and doesn't have a full RunPlan yet.
        """
        source_plan = template.source_plan or {}
        sources = source_plan.get("sources", [])

        run_plan: dict = {
            "version": "1.0",
            "name": template.name,
            "sources": [],
        }

        urls = []
        for src in sources:
            url = src.get("url")
            if url:
                urls.append(url)

        if urls:
            run_plan["sources"].append({
                "type": "url_list",
                "urls": urls,
                "category_hint": template.topic,
            })

        return run_plan
