"""
CPIS V1 — Celery collection task definitions.

Each function represents one stage in the collection pipeline.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.collectors.selector import CollectorSelector
from app.cleaners.html_cleaner import HtmlCleaner
from app.core.database import get_celery_session
from app.core.logging import get_logger
from app.extractors.product_extractor import ProductExtractor
from app.models import SourceSnapshot, TaskStage, TaskStatus
from app.models.collection_task import CollectionTask
from app.repositories.task_repository import TaskRepository
from app.schemas.extraction import ExtractionInput
from app.schemas.task import TaskResponse
from app.services.product_service import ProductVersioningService
from app.tasks import celery_app

logger = get_logger(__name__)

_collector_selector = CollectorSelector(max_per_domain=2)
_html_cleaner = HtmlCleaner()
_product_extractor = ProductExtractor()


# ── Sync entry points (Celery tasks) ──────────────────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def collect_url(self, task_id: str, url: str) -> dict:
    """Fetch the URL content (called by Celery worker)."""
    logger.info("collect_url_started", task_id=task_id, url=url)
    try:
        return asyncio.run(_do_collect(task_id, url))
    except Exception as exc:
        logger.error("collect_url_retrying", task_id=task_id, error=str(exc), exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def clean_content(self, task_id: str) -> dict:
    """Clean the fetched HTML content (Node 07)."""
    logger.info("clean_content_started", task_id=task_id)
    try:
        return asyncio.run(_do_clean(task_id))
    except Exception as exc:
        logger.error("clean_content_retrying", task_id=task_id, error=str(exc), exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def extract_structured_data(self, task_id: str) -> dict:
    """Run AI extraction on cleaned content (Node 08)."""
    logger.info("extract_structured_data_started", task_id=task_id)
    try:
        return asyncio.run(_do_extract(task_id))
    except Exception as exc:
        logger.error("extract_structured_data_retrying", task_id=task_id, error=str(exc), exc_info=True)
        raise self.retry(exc=exc)


# ── Async implementations ────────────────────────────────────


async def _do_collect(task_id: str, url: str) -> dict:
    """Fetch a URL, persist the raw content, and update the task state."""
    tid = uuid.UUID(task_id)
    async with get_celery_session() as session:
        repo = TaskRepository(session)
        start = time.monotonic()

        try:
            await repo.update_status(tid, TaskStatus.FETCHING)
            await repo.create_event(tid, TaskStage.COLLECTION, TaskStatus.FETCHING, message="Starting fetch")

            result = await _collector_selector.fetch(url, timeout=20)

            if not result.success:
                error_code = result.error_code.value if result.error_code else "FETCH_FAILED"
                await repo.update_status(tid, TaskStatus.FAILED, error_code=error_code, error_message=result.error_message)
                await repo.create_event(tid, TaskStage.COLLECTION, TaskStatus.FAILED, message=result.error_message)
                return {"task_id": task_id, "url": url, "status": "failed", "error": result.error_message}

            snapshot = SourceSnapshot(
                task_id=tid,
                final_url=result.final_url,
                html_hash=result.content_hash,
                raw_html=result.raw_html,
            )
            session.add(snapshot)

            duration = int((time.monotonic() - start) * 1000)
            await repo.update_status(tid, TaskStatus.COMPLETED)
            await repo.create_event(
                tid,
                TaskStage.COLLECTION,
                TaskStatus.COMPLETED,
                message=f"Fetched {len(result.raw_html)} bytes",
                duration_ms=duration,
            )

            clean_content.delay(task_id)

            return {
                "task_id": task_id,
                "url": url,
                "status": "completed",
                "collector": "playwright" if result.used_playwright else "httpx",
                "size": len(result.raw_html),
                "final_url": result.final_url,
            }

        except Exception as exc:
            logger.error("collect_url_failed", task_id=task_id, error=str(exc))
            await repo.update_status(tid, TaskStatus.FAILED, error_code="COLLECT_ERROR", error_message=str(exc))
            await repo.create_event(tid, TaskStage.COLLECTION, TaskStatus.FAILED, message=str(exc))
            raise


async def _do_clean(task_id: str) -> dict:
    """Load a raw snapshot, clean the HTML, and persist the result."""
    tid = uuid.UUID(task_id)
    async with get_celery_session() as session:
        repo = TaskRepository(session)
        start = time.monotonic()

        try:
            result = await session.execute(
                select(CollectionTask)
                .options(selectinload(CollectionTask.snapshot))
                .where(CollectionTask.id == tid)
            )
            task = result.scalar_one_or_none()
            if task is None:
                return {"task_id": task_id, "status": "failed", "error": "Task not found"}

            snapshot = task.snapshot
            if snapshot is None or not snapshot.raw_html:
                await repo.update_status(tid, TaskStatus.FAILED, error_code="NO_SNAPSHOT", error_message="No source snapshot found")
                await repo.create_event(tid, TaskStage.CLEANING, TaskStatus.FAILED, message="No source snapshot found")
                return {"task_id": task_id, "status": "failed", "error": "No source snapshot found"}

            await repo.update_status(tid, TaskStatus.CLEANING)
            await repo.create_event(tid, TaskStage.CLEANING, TaskStatus.CLEANING, message="Starting clean")

            clean_result = _html_cleaner.clean(snapshot.raw_html, page_url=snapshot.final_url or "")

            if not clean_result.success:
                await repo.update_status(tid, TaskStatus.FAILED, error_code="CLEAN_FAILED", error_message=clean_result.error_message)
                await repo.create_event(tid, TaskStage.CLEANING, TaskStatus.FAILED, message=clean_result.error_message)
                return {"task_id": task_id, "status": "failed", "error": clean_result.error_message}

            snapshot.cleaned_text = clean_result.cleaned_text
            snapshot.cleaned_markdown = clean_result.cleaned_markdown
            snapshot.content_hash = clean_result.content_hash

            duration = int((time.monotonic() - start) * 1000)
            await repo.update_status(tid, TaskStatus.COMPLETED)
            await repo.create_event(
                tid,
                TaskStage.CLEANING,
                TaskStatus.COMPLETED,
                message=f"Cleaned {len(clean_result.cleaned_text)} chars",
                duration_ms=duration,
            )

            extract_structured_data.delay(task_id)

            return {"task_id": task_id, "status": "completed", "cleaned_length": len(clean_result.cleaned_text)}

        except Exception as exc:
            logger.error("clean_content_failed", task_id=task_id, error=str(exc))
            await repo.update_status(tid, TaskStatus.FAILED, error_code="CLEAN_ERROR", error_message=str(exc))
            await repo.create_event(tid, TaskStage.CLEANING, TaskStatus.FAILED, message=str(exc))
            raise


async def _do_extract(task_id: str) -> dict:
    """Load cleaned content, run AI extraction, and persist the product."""
    tid = uuid.UUID(task_id)
    async with get_celery_session() as session:
        repo = TaskRepository(session)
        start = time.monotonic()

        try:
            result = await session.execute(
                select(CollectionTask)
                .options(selectinload(CollectionTask.snapshot))
                .where(CollectionTask.id == tid)
            )
            task = result.scalar_one_or_none()
            if task is None:
                return {"task_id": task_id, "status": "failed", "error": "Task not found"}

            snapshot = task.snapshot
            if snapshot is None or not snapshot.cleaned_text:
                await repo.update_status(tid, TaskStatus.FAILED, error_code="NO_CLEANED_CONTENT", error_message="No cleaned content found")
                await repo.create_event(tid, TaskStage.EXTRACTION, TaskStatus.FAILED, message="No cleaned content found")
                return {"task_id": task_id, "status": "failed", "error": "No cleaned content found"}

            await repo.update_status(tid, TaskStatus.EXTRACTING)
            await repo.create_event(tid, TaskStage.EXTRACTION, TaskStatus.EXTRACTING, message="Starting extraction")

            extraction_input = ExtractionInput(
                page_title="",
                final_url=snapshot.final_url or "",
                cleaned_text=snapshot.cleaned_text or "",
                cleaned_markdown=snapshot.cleaned_markdown or "",
                category_hint=task.category_hint,
                language_hint=task.language_hint,
            )

            extraction_result = await _product_extractor.extract(extraction_input)

            task_response = TaskResponse.model_validate(task)
            product = await ProductVersioningService(session).process_extraction(
                extraction=extraction_result,
                task=task_response,
                snapshot_id=snapshot.id,
            )

            duration = int((time.monotonic() - start) * 1000)
            await repo.update_status(tid, TaskStatus.COMPLETED)
            await repo.create_event(
                tid,
                TaskStage.EXTRACTION,
                TaskStatus.COMPLETED,
                message=f"Extracted product {product.id}",
                duration_ms=duration,
            )

            return {
                "task_id": task_id,
                "status": "completed",
                "product_id": str(product.id),
                "confidence": extraction_result.overall_confidence,
            }

        except Exception as exc:
            logger.error("extract_structured_data_failed", task_id=task_id, error=str(exc))
            await repo.update_status(tid, TaskStatus.FAILED, error_code="EXTRACT_ERROR", error_message=str(exc))
            await repo.create_event(tid, TaskStage.EXTRACTION, TaskStatus.FAILED, message=str(exc))
            raise
