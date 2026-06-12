"""
CPIS V1 — Celery collection task definitions.

Each function represents one stage in the collection pipeline.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.tasks import celery_app
from app.collectors.selector import CollectorSelector

logger = get_logger(__name__)

# Shared collector selector (reused across tasks)
_collector_selector = CollectorSelector(max_per_domain=2)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def collect_url(self, task_id: str, url: str) -> dict:
    """Fetch the URL content (called by Celery worker).

    This is a Celery task stub — the actual async fetch needs to
    be called from the sync Celery task via asyncio.
    """
    logger.info("collect_url_started", task_id=task_id, url=url)
    # TODO: Integrate async collector via asyncio.run() in production
    # For now, this is a placeholder that returns the task input
    return {
        "task_id": task_id,
        "url": url,
        "status": "pending",
        "collector": "httpx",
    }


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def clean_content(self, task_id: str) -> dict:
    """Clean the fetched HTML content (Node 07)."""
    logger.info("clean_content_started", task_id=task_id)
    return {"task_id": task_id, "status": "pending"}


@celery_app.task(bind=True, max_retries=3, acks_late=True)
def extract_structured_data(self, task_id: str) -> dict:
    """Run AI extraction on cleaned content (Node 08)."""
    logger.info("extract_structured_data_started", task_id=task_id)
    return {"task_id": task_id, "status": "pending"}
