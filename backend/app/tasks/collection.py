"""
CPIS V1 — Celery collection task definitions.

These are the async entry points that the Celery workers execute.
Each function represents one stage in the collection pipeline.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_url(self, task_id: str) -> dict:
    """Fetch the URL content (called by Celery worker).

    This is a placeholder — the actual fetching logic will be
    implemented in Node 06 (Web Fetcher).
    """
    logger.info("collect_url_started", task_id=task_id)
    # TODO: Implement in Node 06
    return {"task_id": task_id, "status": "pending"}


@celery_app.task(bind=True)
def clean_content(self, task_id: str) -> dict:
    """Clean the fetched HTML content (Node 07)."""
    logger.info("clean_content_started", task_id=task_id)
    # TODO: Implement in Node 07
    return {"task_id": task_id, "status": "pending"}


@celery_app.task(bind=True)
def extract_structured_data(self, task_id: str) -> dict:
    """Run AI extraction on cleaned content (Node 08)."""
    logger.info("extract_structured_data_started", task_id=task_id)
    # TODO: Implement in Node 08
    return {"task_id": task_id, "status": "pending"}
