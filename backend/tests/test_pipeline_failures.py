"""
CPIS V1 — Pipeline failure path tests.

Verifies graceful handling of: network timeout, HTTP 500, empty HTML,
LLM extraction failure, and Celery task retry on transient failures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Base, CollectionTask, SourceSnapshot, TaskEvent
from app.models.enums import TaskStage, TaskStatus
from app.collectors.base import CollectResult, FetchErrorCode
from app.extractors.ai_provider import AIProviderError
from app.extractors.product_extractor import ProductExtractor

SAMPLE_HTML = b"""<html><head><title>TechPro X100</title></head>
<body><h1>TechPro X100</h1><p class="price">$299.99</p>
<p>The TechPro X100 is a premium EMS muscle stimulator.</p>
<ul><li>8 working modes</li><li>20 levels</li></ul></body></html>"""


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=NullPool)
    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


def _mock_celery_session_cm(db_session: AsyncSession) -> AsyncMock:
    cm = AsyncMock()
    cm.__aenter__.return_value = db_session
    cm.__aexit__.return_value = None
    return cm


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestCollectStageFailures:
    """Failure paths in the collect stage (_do_collect)."""

    @pytest.mark.asyncio
    async def test_network_timeout_sets_failed(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/timeout",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        fetch_result = CollectResult(
            success=False,
            error_code=FetchErrorCode.FETCH_TIMEOUT,
            error_message="Request timed out after 20s",
        )
        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.tasks.collection._collector_selector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
        ):
            result = await _do_collect(task_id, "https://example.com/timeout")

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "FETCH_TIMEOUT"
        assert result["status"] == "failed"

        events_result = await db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task.id)
            .order_by(TaskEvent.created_at)
        )
        events = list(events_result.scalars().all())
        failed_events = [e for e in events if e.status == TaskStatus.FAILED.value]
        assert len(failed_events) >= 1
        assert failed_events[-1].stage == TaskStage.COLLECTION.value

    @pytest.mark.asyncio
    async def test_http_500_graceful_handling(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/server-error",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        fetch_result = CollectResult(
            success=False,
            http_status=500,
            error_code=FetchErrorCode.FETCH_HTTP_ERROR,
            error_message="HTTP 500 Internal Server Error",
        )
        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.tasks.collection._collector_selector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
        ):
            result = await _do_collect(task_id, "https://example.com/server-error")

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "FETCH_HTTP_ERROR"
        assert task.error_message == "HTTP 500 Internal Server Error"
        assert result["status"] == "failed"


class TestCleanStageFailures:
    """Failure paths in the clean stage (_do_clean)."""

    @pytest.mark.asyncio
    async def test_empty_html_clean_graceful(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_clean

        task = CollectionTask(
            source_url="https://example.com/empty",
            status=TaskStatus.FETCHING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/empty",
            raw_html=b"   ",
            html_hash="empty",
        )
        db_session.add(snapshot)
        await db_session.flush()
        task_id = str(task.id)

        mock_cm = _mock_celery_session_cm(db_session)

        with patch("app.tasks.collection.get_celery_session", return_value=mock_cm):
            result = await _do_clean(task_id)

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "CLEAN_FAILED"
        assert "Empty" in (task.error_message or "")
        assert result["status"] == "failed"

        events_result = await db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task.id)
            .order_by(TaskEvent.created_at)
        )
        events = list(events_result.scalars().all())
        failed_events = [e for e in events if e.status == TaskStatus.FAILED.value]
        assert len(failed_events) >= 1
        assert failed_events[-1].stage == TaskStage.CLEANING.value


class TestExtractStageFailures:
    """Failure paths in the extract stage (_do_extract)."""

    @pytest.mark.asyncio
    async def test_llm_extraction_failure_sets_failed(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_extract

        task = CollectionTask(
            source_url="https://example.com/product",
            domain="example.com",
            status=TaskStatus.CLEANING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/product",
            raw_html=SAMPLE_HTML,
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="abc123",
        )
        db_session.add(snapshot)
        await db_session.flush()
        task_id = str(task.id)

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch.object(
                ProductExtractor,
                "extract",
                new=AsyncMock(side_effect=AIProviderError("LLM unavailable")),
            ),
        ):
            with pytest.raises(AIProviderError, match="LLM unavailable"):
                await _do_extract(task_id)

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "EXTRACT_ERROR"
        assert "LLM unavailable" in (task.error_message or "")

        events_result = await db_session.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task.id)
            .order_by(TaskEvent.created_at)
        )
        events = list(events_result.scalars().all())
        failed_events = [e for e in events if e.status == TaskStatus.FAILED.value]
        assert len(failed_events) >= 1
        assert failed_events[-1].stage == TaskStage.EXTRACTION.value


class TestCeleryRetry:
    """Celery task wrappers retry on transient failures."""

    def _retry_signal(self, *a, **kw):
        raise RetrySignal()

    @pytest.mark.asyncio
    async def test_do_collect_reraises_for_retry(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/crash",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.tasks.collection._collector_selector.fetch",
                new=AsyncMock(side_effect=RuntimeError("Unexpected crash")),
            ),
        ):
            with pytest.raises(RuntimeError, match="Unexpected crash"):
                await _do_collect(task_id, "https://example.com/crash")

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "COLLECT_ERROR"

    def test_retry_configuration(self) -> None:
        from app.tasks.collection import collect_url, clean_content, extract_structured_data

        for task in (collect_url, clean_content, extract_structured_data):
            assert task.max_retries == 3
            assert task.acks_late is True

        assert collect_url.default_retry_delay == 60
