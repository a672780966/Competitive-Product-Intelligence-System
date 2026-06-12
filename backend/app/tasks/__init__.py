"""
CPIS V1 — Celery worker configuration.

Usage:
    celery -A app.tasks.worker worker --loglevel=info
"""

from __future__ import annotations

from celery import Celery

from app.core import get_settings

settings = get_settings()

celery_app = Celery(
    "cpis-v1",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600 * 24 * 7,  # 7 days
)
