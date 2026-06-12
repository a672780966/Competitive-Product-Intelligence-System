"""
CPIS V1 — Celery collection task definitions.

Implements the full collection pipeline as Celery tasks:
  PENDING → FETCHING → CLEANING → EXTRACTING
  → REVIEW_PENDING / SYNCING → COMPLETED

Each task receives only task_id (and optional snapshot_id/product_id),
never large objects like HTML content.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from app.collectors.selector import CollectorSelector
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models import SourceSnapshot
from app.models.enums import ReviewStatus, SyncStatus, TaskStage, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.services.product_service import ProductVersioningService
from app.tasks import celery_app

logger = get_logger(__name__)

# Shared resources
_collector_selector = CollectorSelector(max_per_domain=2)


# ── Orchestrator task ─────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=0, acks_late=True)
def run_collection_pipeline(self, task_id: str) -> dict:
    """Entry point: run the full collection pipeline for a task.

    Dispatched after URL validation passes.
    The pipeline runs sequentially: fetch → clean → extract → version.

    Args:
        task_id: The CollectionTask UUID string.

    Returns:
        Dict with final status and product_id (if created).
    """
    logger.info("pipeline_started", task_id=task_id)

    try:
        # Stage 1: Fetch URL
        snapshot_id = _run_async(_fetch_stage(task_id))
        if snapshot_id is None:
            return {"task_id": task_id, "status": "failed", "stage": "fetch"}

        # Stage 2: Clean content
        cleaned = _run_async(_clean_stage(task_id, snapshot_id))
        if not cleaned:
            return {"task_id": task_id, "status": "failed", "stage": "clean"}

        # Stage 3: AI extract
        extraction = _run_async(_extract_stage(task_id, snapshot_id))
        if extraction is None:
            return {"task_id": task_id, "status": "failed", "stage": "extract"}

        # Stage 4: Product versioning
        product_id = _run_async(_version_stage(task_id, snapshot_id, extraction))
        if product_id is None:
            return {"task_id": task_id, "status": "failed", "stage": "version"}

        # Stage 5: Feishu sync (if auto-approved + auto_sync_feishu)
        _run_async(_sync_stage(task_id, product_id))

        return {
            "task_id": task_id,
            "status": "completed",
            "product_id": str(product_id) if product_id else None,
        }

    except Exception as exc:
        logger.error("pipeline_unhandled_error", task_id=task_id, error=str(exc))
        _run_async(_set_task_failed(task_id, "PIPELINE_ERROR", str(exc)))
        return {"task_id": task_id, "status": "failed", "error": str(exc)}


# ── Pipeline stages (async) ───────────────────────────────────────


async def _fetch_stage(task_id: str) -> str | None:
    """Stage 1: Fetch URL content.

    Returns snapshot_id string, or None on failure.
    """
    uid = uuid.UUID(task_id)
    async with async_session_factory() as db:
        repo = TaskRepository(db)

        # Idempotency check
        task = await repo.get_by_id(uid)
        if task is None:
            logger.error("task_not_found", task_id=task_id)
            return None

        # If already completed/cancelled, skip
        if task.status in (_t(TaskStatus.COMPLETED), _t(TaskStatus.CANCELLED)):
            logger.info("task_skipped_idempotent", task_id=task_id, status=task.status)
            return None

        # Check for cancellation before starting
        if task.status == _t(TaskStatus.CANCELLED):
            return None

        start = time.monotonic()
        await repo.update_status(uid, TaskStatus.FETCHING)

        # Fetch the URL
        url = task.normalized_url or task.source_url
        result = await _collector_selector.fetch(url)

        duration = int((time.monotonic() - start) * 1000)

        if not result.success:
            error_code = result.error_code.value if result.error_code else "FETCH_FAILED"
            await repo.update_status(uid, TaskStatus.FAILED, error_code=error_code, error_message=result.error_message)
            await repo.create_event(uid, TaskStage.COLLECTION.value, TaskStatus.FAILED,
                                    message=result.error_message, duration_ms=duration, error_code=error_code)
            return None

        # Save snapshot
        snapshot = SourceSnapshot(
            task_id=uid,
            final_url=result.final_url or url,
            html_hash=result.content_hash,
            raw_html=result.raw_html,
        )
        db.add(snapshot)
        await db.flush()

        await repo.create_event(uid, TaskStage.COLLECTION.value, TaskStatus.COMPLETED,
                                message=f"Fetched {len(result.raw_html)} bytes from {result.final_url or url}",
                                duration_ms=duration)
        logger.info("fetch_completed", task_id=task_id, bytes=len(result.raw_html), duration_ms=duration)
        return str(snapshot.id)


async def _clean_stage(task_id: str, snapshot_id: str) -> bool:
    """Stage 2: Clean fetched HTML content.

    Returns True on success.
    """
    from app.cleaners.html_cleaner import HtmlCleaner

    uid = uuid.UUID(task_id)
    sid = uuid.UUID(snapshot_id)

    async with async_session_factory() as db:
        repo = TaskRepository(db)

        task = await repo.get_by_id(uid)
        if task is None or task.status == _t(TaskStatus.CANCELLED):
            return False

        start = time.monotonic()
        await repo.update_status(uid, TaskStatus.CLEANING)

        # Get snapshot
        result = await db.execute(
            __import__("sqlalchemy").select(SourceSnapshot).where(SourceSnapshot.id == sid)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None or not snapshot.raw_html:
            await repo.update_status(uid, TaskStatus.FAILED, error_code="SNAPSHOT_MISSING",
                                     error_message="Snapshot or raw HTML not found")
            await repo.create_event(uid, TaskStage.CLEANING.value, TaskStatus.FAILED,
                                    message="Snapshot not found", error_code="SNAPSHOT_MISSING")
            return False

        # Clean
        cleaner = HtmlCleaner()
        clean_result = cleaner.clean(snapshot.raw_html, page_url=snapshot.final_url or "")

        duration = int((time.monotonic() - start) * 1000)

        if not clean_result.success:
            await repo.update_status(uid, TaskStatus.FAILED, error_code="CLEAN_FAILED",
                                     error_message=clean_result.error_message)
            await repo.create_event(uid, TaskStage.CLEANING.value, TaskStatus.FAILED,
                                    message=clean_result.error_message, duration_ms=duration,
                                    error_code="CLEAN_FAILED")
            return False

        # Update snapshot with cleaned content
        snapshot.cleaned_text = clean_result.cleaned_text
        snapshot.cleaned_markdown = clean_result.cleaned_markdown
        snapshot.content_hash = clean_result.content_hash
        await db.flush()

        await repo.create_event(uid, TaskStage.CLEANING.value, TaskStatus.COMPLETED,
                                message=f"Cleaned {len(clean_result.cleaned_text)} chars",
                                duration_ms=duration)
        logger.info("clean_completed", task_id=task_id, chars=len(clean_result.cleaned_text), duration_ms=duration)
        return True


async def _extract_stage(task_id: str, snapshot_id: str) -> dict | None:
    """Stage 3: Run AI extraction on cleaned content.

    Returns serialized ExtractionResult dict, or None on failure.
    """
    from app.extractors.product_extractor import ProductExtractor
    from app.schemas.extraction import ExtractionInput

    uid = uuid.UUID(task_id)
    sid = uuid.UUID(snapshot_id)

    async with async_session_factory() as db:
        repo = TaskRepository(db)

        task = await repo.get_by_id(uid)
        if task is None or task.status == _t(TaskStatus.CANCELLED):
            return None

        start = time.monotonic()
        await repo.update_status(uid, TaskStatus.EXTRACTING)

        # Get snapshot with cleaned content
        result = await db.execute(
            __import__("sqlalchemy").select(SourceSnapshot).where(SourceSnapshot.id == sid)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None or not snapshot.cleaned_text:
            await repo.update_status(uid, TaskStatus.FAILED, error_code="CLEANED_CONTENT_MISSING",
                                     error_message="Cleaned text not found")
            await repo.create_event(uid, TaskStage.EXTRACTION.value, TaskStatus.FAILED,
                                    message="Cleaned text not found", error_code="CLEANED_CONTENT_MISSING")
            return None

        # Build extraction input
        inp = ExtractionInput(
            cleaned_text=snapshot.cleaned_text,
            cleaned_markdown=snapshot.cleaned_markdown or "",
            final_url=snapshot.final_url or "",
        )

        # Run extraction
        extractor = ProductExtractor()
        extraction = await extractor.extract(inp)

        duration = int((time.monotonic() - start) * 1000)

        if extraction.overall_confidence == 0.0 and extraction.missing_fields:
            await repo.update_status(uid, TaskStatus.FAILED, error_code="EXTRACTION_FAILED",
                                     error_message="AI extraction returned empty result")
            await repo.create_event(uid, TaskStage.EXTRACTION.value, TaskStatus.FAILED,
                                    message="AI extraction failed", duration_ms=duration,
                                    error_code="EXTRACTION_FAILED")
            return None

        await repo.create_event(uid, TaskStage.EXTRACTION.value, TaskStatus.COMPLETED,
                                message=f"Extracted {len(extraction.structured_data.model_dump())} fields, "
                                        f"confidence={extraction.overall_confidence:.2f}",
                                duration_ms=duration)
        logger.info("extract_completed", task_id=task_id, confidence=extraction.overall_confidence, duration_ms=duration)

        # Serialize for passing through Celery (small metadata only)
        return extraction.model_dump()


async def _version_stage(task_id: str, snapshot_id: str, extraction_data: dict) -> str | None:
    """Stage 4: Create product version from extraction result.

    Returns product_id string, or None on failure.
    """
    from app.schemas.extraction import ExtractionResult
    from app.schemas.task import TaskResponse

    uid = uuid.UUID(task_id)
    sid = uuid.UUID(snapshot_id)

    async with async_session_factory() as db:
        repo = TaskRepository(db)

        task = await repo.get_by_id(uid)
        if task is None or task.status == _t(TaskStatus.CANCELLED):
            return None

        start = time.monotonic()

        # Reconstruct domain info for TaskResponse
        task_resp = TaskResponse(
            id=task.id,
            source_url=task.source_url,
            normalized_url=task.normalized_url,
            domain=task.domain,
            status=task.status if isinstance(task.status, str) else task.status.value,
            priority=task.priority if isinstance(task.priority, int) else task.priority.value,
            auto_sync_feishu=task.auto_sync_feishu,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

        # Reconstruct extraction
        extraction = ExtractionResult(**extraction_data)

        # Create product + version
        svc = ProductVersioningService(db)
        product = await svc.process_extraction(extraction, task_resp, snapshot_id=sid)

        duration = int((time.monotonic() - start) * 1000)

        # Update task status based on review outcome
        if product.review_status == _t(ReviewStatus.AUTO_APPROVED):
            new_status = TaskStatus.COMPLETED
        elif product.review_status in (_t(ReviewStatus.NEEDS_REVIEW), _t(ReviewStatus.PENDING)):
            new_status = TaskStatus.REVIEW_PENDING
        else:
            new_status = TaskStatus.COMPLETED

        await repo.update_status(uid, new_status)
        await repo.create_event(uid, TaskStage.EXTRACTION.value, new_status,
                                message=f"Product {product.id} v{product.review_status}",
                                duration_ms=duration)
        logger.info("version_completed", task_id=task_id, product_id=str(product.id), status=new_status.value)
        return str(product.id)


async def _sync_stage(task_id: str, product_id: str) -> None:
    """Stage 5: Sync to Feishu if auto-approved and auto_sync_feishu=True."""
    from app.services.feishu_sync_service import FeishuSyncService

    uid = uuid.UUID(task_id)
    pid = uuid.UUID(product_id)

    async with async_session_factory() as db:
        repo = TaskRepository(db)

        task = await repo.get_by_id(uid)
        if task is None or task.status == _t(TaskStatus.CANCELLED):
            return

        # Only sync if auto_sync_feishu is set
        if not task.auto_sync_feishu:
            return

        start = time.monotonic()
        await repo.update_status(uid, TaskStatus.SYNCING)
        await repo.create_event(uid, TaskStage.SYNC.value, TaskStatus.SYNCING,
                                message="Starting Feishu sync")

        try:
            sync_svc = FeishuSyncService(db)
            sync_record = await sync_svc.sync_product(pid)

            duration = int((time.monotonic() - start) * 1000)
            if sync_record.sync_status == _t(SyncStatus.SUCCESS):
                await repo.update_status(uid, TaskStatus.COMPLETED)
                await repo.create_event(uid, TaskStage.SYNC.value, TaskStatus.COMPLETED,
                                        message=f"Synced to Feishu: {sync_record.feishu_record_id}",
                                        duration_ms=duration)
            else:
                await repo.update_status(uid, TaskStatus.PARTIAL_SUCCESS,
                                         error_code="SYNC_FAILED",
                                         error_message=sync_record.error_message)
                await repo.create_event(uid, TaskStage.SYNC.value, TaskStatus.PARTIAL_SUCCESS,
                                        message=f"Sync failed: {sync_record.error_message}",
                                        duration_ms=duration, error_code="SYNC_FAILED")
        except Exception as exc:
            duration = int((time.monotonic() - start) * 1000)
            logger.error("sync_stage_error", task_id=task_id, error=str(exc))
            await repo.update_status(uid, TaskStatus.PARTIAL_SUCCESS, error_code="SYNC_ERROR",
                                     error_message=str(exc))
            await repo.create_event(uid, TaskStage.SYNC.value, TaskStatus.PARTIAL_SUCCESS,
                                    message=f"Sync error: {exc}", duration_ms=duration,
                                    error_code="SYNC_ERROR")


async def _set_task_failed(task_id: str, error_code: str, error_message: str) -> None:
    """Set a task to FAILED status with error info."""
    uid = uuid.UUID(task_id)
    async with async_session_factory() as db:
        repo = TaskRepository(db)
        await repo.update_status(uid, TaskStatus.FAILED, error_code=error_code, error_message=error_message)
        await repo.create_event(uid, "pipeline", TaskStatus.FAILED, message=error_message, error_code=error_code)


# ── Standalone stage tasks (for individual dispatch) ──────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True,
                 autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=600)
def collect_url(self, task_id: str) -> dict:
    """Fetch the URL content (standalone Celery task)."""
    logger.info("collect_url_started", task_id=task_id)
    result = _run_async(_fetch_stage(task_id))
    if result is None:
        raise self.retry(countdown=60)
    return {"task_id": task_id, "snapshot_id": result, "status": "completed"}


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def clean_content(self, task_id: str, snapshot_id: str) -> dict:
    """Clean the fetched HTML content."""
    logger.info("clean_content_started", task_id=task_id)
    success = _run_async(_clean_stage(task_id, snapshot_id))
    return {"task_id": task_id, "status": "completed" if success else "failed"}


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def extract_structured_data(self, task_id: str, snapshot_id: str) -> dict:
    """Run AI extraction on cleaned content."""
    logger.info("extract_structured_data_started", task_id=task_id)
    result = _run_async(_extract_stage(task_id, snapshot_id))
    if result is None:
        return {"task_id": task_id, "status": "failed"}
    return {"task_id": task_id, "status": "completed", "extraction": result}


# ── Helper ────────────────────────────────────────────────────────


def _run_async(coro):
    """Run an async coroutine from a sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _t(enum_val) -> str:
    """Get the string value from an enum member."""
    return enum_val.value if hasattr(enum_val, "value") else str(enum_val)
