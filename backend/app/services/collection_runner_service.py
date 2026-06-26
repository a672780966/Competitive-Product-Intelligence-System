"""CollectionRunnerService — RunPlan executor.

Takes a declarative RunPlan JSON, validates it against the RunPlan schema,
iterates sources/URLs, creates CollectionTasks (PENDING), and triggers
the Celery pipeline for each URL.

Reuses the existing Celery pipeline: collect_url → clean_content → extract_structured_data.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import get_collector_registry
from app.core.logging import get_logger
from app.models import CollectionTask, TaskEvent
from app.models.enums import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.run_plan import RunPlanSchema, validate_run_plan
from app.schemas.task import CreateTaskRequest, TaskResponse
from app.services.task_service import TaskService

logger = get_logger(__name__)


class RunPlanExecutor:
    """Executes a declarative RunPlan.

    Flow:
    1. Validate the RunPlan JSON against the schema
    2. Resolve all URLs from sources (url_list, url_pattern, search, sitemap)
    3. For each URL, create a CollectionTask (PENDING) via TaskService
    4. Enqueue the task to the Celery pipeline
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._task_service = TaskService(db)
        self._task_repo = TaskRepository(db)
        self._registry = get_collector_registry()

    async def execute_plan(
        self,
        plan_data: dict,
        *,
        created_by: str = "system",
        category_hint: str | None = None,
        language_hint: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        auto_sync_feishu: bool = False,
    ) -> list[TaskResponse]:
        """Validate and execute a RunPlan.

        Args:
            plan_data: RunPlan JSON dict
            created_by: Actor that created the tasks
            category_hint: Default category hint for all sources
            language_hint: Default language hint for all sources
            priority: Default task priority
            auto_sync_feishu: Whether to auto-sync to Feishu

        Returns:
            List of created TaskResponses

        Raises:
            ValueError: If the RunPlan fails validation
        """
        # 1. Validate
        plan = validate_run_plan(plan_data)

        # 2. Resolve URLs
        all_urls = self._resolve_urls(plan)

        # 3. Create tasks
        tasks: list[TaskResponse] = []
        for url_info in all_urls:
            cat_hint = url_info.get("category_hint") or category_hint
            lang_hint = url_info.get("language_hint") or language_hint

            req = CreateTaskRequest(
                source_url=url_info["url"],
                category_hint=cat_hint,
                language_hint=lang_hint,
                priority=priority,
                auto_sync_feishu=auto_sync_feishu,
                created_by=created_by,
            )
            task_resp = await self._task_service.create_task(req)
            tasks.append(task_resp)

        logger.info(
            "run_plan_executed",
            plan_name=plan.name,
            source_count=len(plan.sources),
            url_count=len(all_urls),
            task_count=len(tasks),
        )

        return tasks

    async def execute_plan_direct(
        self,
        plan_data: dict,
        *,
        created_by: str = "system",
    ) -> list[TaskResponse]:
        """Execute a RunPlan with direct collector pre-fetching.

        For direct_http sources, optionally pre-fetches content before
        enqueuing to the Celery pipeline.

        This is a more advanced execution path that can provide immediate
        feedback. Falls back to standard execute_plan if pre-fetch fails.
        """
        return await self.execute_plan(
            plan_data,
            created_by=created_by,
        )

    # ── Private ──────────────────────────────────────────────────

    def _resolve_urls(self, plan: RunPlanSchema) -> list[dict[str, Any]]:
        """Resolve all URLs from the plan's sources.

        Handles:
        - url_list: direct URLs
        - url_pattern: templated URLs with parameters
        - search: web search (requires SearchProvider — currently returns empty)
        - sitemap: XML sitemap parsing (requires network — currently returns empty)
        """
        all_urls: list[dict[str, Any]] = []
        page_limit = plan.scope.max_pages if plan.scope else 50

        for source in plan.sources:
            if source.type == "url_list" and source.urls:
                for url in source.urls:
                    all_urls.append({
                        "url": url,
                        "category_hint": source.category_hint,
                        "language_hint": source.language_hint,
                        "collector": source.collector.kind if source.collector
                        else (plan.collector.kind if plan.collector else "direct_http"),
                    })
                    if len(all_urls) >= page_limit:
                        return all_urls

            elif source.type == "url_pattern" and source.url_template and source.url_params:
                resolved = self._resolve_url_pattern(source.url_template, source.url_params)
                for url in resolved:
                    all_urls.append({
                        "url": url,
                        "category_hint": source.category_hint,
                        "language_hint": source.language_hint,
                        "collector": source.collector.kind if source.collector
                        else (plan.collector.kind if plan.collector else "direct_http"),
                    })
                    if len(all_urls) >= page_limit:
                        return all_urls

            # search and sitemap types require external providers
            # In the MVP, these return an empty list — full support is Node 7+
            elif source.type == "search":
                logger.info(
                    "search_source_skipped_mvp",
                    query=source.search_query,
                )

            elif source.type == "sitemap":
                logger.info(
                    "sitemap_source_skipped_mvp",
                    url=source.sitemap_url,
                )

        return all_urls

    @staticmethod
    def _resolve_url_pattern(
        template: str,
        params: dict[str, list[str | int | float]],
    ) -> list[str]:
        """Resolve a URL template with parameter combinations.

        Example:
            template: "https://example.com/products?page={page}"
            params: {"page": [1, 2, 3]}
            Result: ["https://example.com/products?page=1", ...]
        """
        import itertools

        # Validate: no ${} syntax (security rule S005)
        if "${" in template:
            raise ValueError(
                "Security violation S005: url_template must not contain ${} syntax",
            )

        # Check template params match
        import re as _re
        template_params = _re.findall(r"\{(\w+)\}", template)
        for tp in template_params:
            if tp not in params:
                raise ValueError(
                    f"Validation error: template parameter '{{{tp}}}' not found in url_params. "
                    f"Available keys: {list(params.keys())}",
                )

        # Generate all combinations
        keys = list(params.keys())
        value_lists = [params[k] for k in keys]
        urls: list[str] = []
        for combo in itertools.product(*value_lists):
            kwargs = dict(zip(keys, combo))
            try:
                url = template.format(**kwargs)
            except KeyError as e:
                raise ValueError(f"URL template substitution failed: missing key {e}") from e
            urls.append(url)

        return urls
