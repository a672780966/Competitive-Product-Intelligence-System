"""
CPIS V1 — 管道测试（模拟网络/LLM）

Tests the collect → clean → extract → version pipeline with mocked
network calls (httpx, Playwright) and LLM extraction calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from sqlalchemy import select

from app.models import Base, CollectionTask, Product, SourceSnapshot
from app.models.enums import TaskStatus
from app.collectors.base import CollectResult, FetchErrorCode
from app.cleaners.html_cleaner import CleanResult
from app.schemas.extraction import (
    ExtractionResult,
    ProductAnalysisFields,
    ProductFactFields,
)


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


# ══════════════════════════════════════════════════════════════════
# Stage 1: collect_url
# ══════════════════════════════════════════════════════════════════


class TestCollectStage:
    """collect_url — _do_collect creates SourceSnapshot on success."""

    @pytest.mark.asyncio
    async def test_collect_creates_source_snapshot(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/techpro-x100",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        fetch_result = CollectResult(
            success=True,
            final_url="https://example.com/techpro-x100",
            http_status=200,
            page_title="TechPro X100",
            raw_html=SAMPLE_HTML,
            content_hash="abc123def456",
            fetch_time_ms=150,
            used_playwright=False,
        )

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.collectors.direct_http.DirectHttpCollector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
            patch("app.tasks.collection.clean_content.delay") as mock_delay,
        ):
            result = await _do_collect(task_id, "https://example.com/techpro-x100")

        await db_session.refresh(task)
        # Query snapshot directly (relationship lazy load fails in async)
        snap_result = await db_session.execute(
            select(SourceSnapshot).where(SourceSnapshot.task_id == task.id)
        )
        snapshot = snap_result.scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.raw_html == SAMPLE_HTML
        assert snapshot.final_url == "https://example.com/techpro-x100"
        assert task.status == TaskStatus.COMPLETED.value
        mock_delay.assert_called_once_with(task_id)
        assert result["status"] == "completed"
        assert result["collector"] == "direct_http"
        assert result["size"] == len(SAMPLE_HTML)

    @pytest.mark.asyncio
    async def test_collect_http_error_marks_task_failed(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/not-found",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        fetch_result = CollectResult(
            success=False,
            http_status=404,
            error_code=FetchErrorCode.FETCH_HTTP_ERROR,
            error_message="HTTP 404",
        )

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.collectors.direct_http.DirectHttpCollector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
        ):
            result = await _do_collect(task_id, "https://example.com/not-found")

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert task.error_code == "FETCH_HTTP_ERROR"
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_collect_uses_httpx_under_the_hood(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect

        task = CollectionTask(
            source_url="https://example.com/techpro-x100",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.content = SAMPLE_HTML
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.url = httpx.URL("https://example.com/techpro-x100")

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client_cls,
            patch("app.tasks.collection.clean_content.delay"),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await _do_collect(task_id, "https://example.com/techpro-x100")

        await db_session.refresh(task)
        snap_result = await db_session.execute(
            select(SourceSnapshot).where(SourceSnapshot.task_id == task.id)
        )
        snapshot = snap_result.scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.raw_html == SAMPLE_HTML
        assert result["status"] == "completed"
        assert result["collector"] == "direct_http"


# ══════════════════════════════════════════════════════════════════
# Stage 2: clean_content
# ══════════════════════════════════════════════════════════════════


class TestCleanStage:
    """clean_content — _do_clean updates SourceSnapshot with cleaned text."""

    @pytest.mark.asyncio
    async def test_clean_updates_snapshot(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_clean

        task = CollectionTask(
            source_url="https://example.com/techpro-x100",
            status=TaskStatus.FETCHING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/techpro-x100",
            raw_html=SAMPLE_HTML,
            html_hash="abc123",
        )
        db_session.add(snapshot)
        await db_session.flush()
        task_id = str(task.id)

        clean_result = CleanResult(
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456",
            success=True,
        )

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch("app.tasks.collection._html_cleaner.clean", return_value=clean_result),
            patch("app.tasks.collection.extract_structured_data.delay") as mock_delay,
        ):
            result = await _do_clean(task_id)

        await db_session.refresh(task)
        snap_result = await db_session.execute(
            select(SourceSnapshot).where(SourceSnapshot.task_id == task.id)
        )
        updated_snapshot = snap_result.scalar_one_or_none()
        assert updated_snapshot is not None
        assert updated_snapshot.cleaned_text == "TechPro X100 $299.99"
        assert updated_snapshot.cleaned_markdown == "# TechPro X100"
        assert updated_snapshot.content_hash == "def456"
        assert task.status == TaskStatus.COMPLETED.value
        mock_delay.assert_called_once_with(task_id)
        assert result["status"] == "completed"
        assert result["cleaned_length"] == len("TechPro X100 $299.99")

    @pytest.mark.asyncio
    async def test_clean_missing_snapshot(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_clean

        task = CollectionTask(
            source_url="https://example.com/test",
            status=TaskStatus.FETCHING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
        ):
            result = await _do_clean(task_id)

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert result["status"] == "failed"
        assert "No source snapshot" in (result.get("error") or "")


# ══════════════════════════════════════════════════════════════════
# Stage 3: extract_structured_data
# ══════════════════════════════════════════════════════════════════


class TestExtractStage:
    """extract_structured_data — _do_extract calls ProductVersioningService."""

    @pytest.mark.asyncio
    async def test_extract_calls_product_versioning(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_extract
        from app.extractors.product_extractor import ProductExtractor
        from app.services.product_service import ProductVersioningService

        task = CollectionTask(
            source_url="https://example.com/techpro-x100",
            domain="example.com",
            status=TaskStatus.CLEANING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/techpro-x100",
            raw_html=SAMPLE_HTML,
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456",
        )
        db_session.add(snapshot)
        await db_session.flush()
        task_id = str(task.id)

        extraction_result = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp",
                product_name="TechPro X100",
                model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )

        fake_product = MagicMock(spec=Product)
        fake_product.id = uuid.uuid4()

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch.object(
                ProductExtractor,
                "extract",
                new=AsyncMock(return_value=extraction_result),
            ),
            patch.object(
                ProductVersioningService,
                "process_extraction",
                new=AsyncMock(return_value=fake_product),
            ) as mock_process,
        ):
            result = await _do_extract(task_id)

        mock_process.assert_called_once()
        kwargs = mock_process.call_args.kwargs
        assert kwargs["snapshot_id"] == snapshot.id
        assert kwargs["extraction"].structured_data.brand == "TechCorp"
        assert kwargs["extraction"].overall_confidence == 0.85

        await db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value
        assert result["status"] == "completed"
        assert result["product_id"] == str(fake_product.id)
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_extract_missing_cleaned_content(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_extract

        task = CollectionTask(
            source_url="https://example.com/test",
            status=TaskStatus.CLEANING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            raw_html=SAMPLE_HTML,
            cleaned_text=None,
        )
        db_session.add(snapshot)
        await db_session.flush()
        task_id = str(task.id)

        mock_cm = _mock_celery_session_cm(db_session)

        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
        ):
            result = await _do_extract(task_id)

        await db_session.refresh(task)
        assert task.status == TaskStatus.FAILED.value
        assert result["status"] == "failed"


# ══════════════════════════════════════════════════════════════════
# Full Pipeline Chain
# ══════════════════════════════════════════════════════════════════


class TestPipelineChain:
    """End-to-end chain: collect → clean → extract (all mocked)."""

    @pytest.mark.asyncio
    async def test_full_chain(self, db_session: AsyncSession) -> None:
        from app.tasks.collection import _do_collect, _do_clean, _do_extract
        from app.extractors.product_extractor import ProductExtractor
        from app.services.product_service import ProductVersioningService

        task = CollectionTask(
            source_url="https://example.com/techpro-x100",
            domain="example.com",
            status=TaskStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()
        task_id = str(task.id)

        fetch_result = CollectResult(
            success=True,
            final_url="https://example.com/techpro-x100",
            http_status=200,
            page_title="TechPro X100",
            raw_html=SAMPLE_HTML,
            content_hash="abc123def456",
            fetch_time_ms=150,
            used_playwright=False,
        )
        clean_result = CleanResult(
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456",
            success=True,
        )
        extraction_result = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp",
                product_name="TechPro X100",
                model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )
        fake_product = MagicMock(spec=Product)
        fake_product.id = uuid.uuid4()

        mock_cm = _mock_celery_session_cm(db_session)

        # Stage 1: collect
        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.collectors.direct_http.DirectHttpCollector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
            patch("app.tasks.collection.clean_content.delay"),
        ):
            result1 = await _do_collect(task_id, "https://example.com/techpro-x100")

        await db_session.refresh(task)
        snap_result = await db_session.execute(
            select(SourceSnapshot).where(SourceSnapshot.task_id == task.id)
        )
        snapshot = snap_result.scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.raw_html == SAMPLE_HTML
        snapshot_id = snapshot.id

        # Stage 2: clean
        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch("app.tasks.collection._html_cleaner.clean", return_value=clean_result),
            patch("app.tasks.collection.extract_structured_data.delay"),
        ):
            result2 = await _do_clean(task_id)

        await db_session.refresh(task)
        snap_result2 = await db_session.execute(
            select(SourceSnapshot).where(SourceSnapshot.task_id == task.id)
        )
        snapshot2 = snap_result2.scalar_one_or_none()
        assert snapshot2 is not None
        assert result2["status"] == "completed"
        assert snapshot2.cleaned_text == "TechPro X100 $299.99"

        # Stage 3: extract
        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch.object(
                ProductExtractor,
                "extract",
                new=AsyncMock(return_value=extraction_result),
            ),
            patch.object(
                ProductVersioningService,
                "process_extraction",
                new=AsyncMock(return_value=fake_product),
            ) as mock_process,
        ):
            result3 = await _do_extract(task_id)

        await db_session.refresh(task)
        assert result3["status"] == "completed"
        assert result3["product_id"] == str(fake_product.id)
        assert result3["confidence"] == 0.85

        mock_process.assert_called_once()
        kwargs = mock_process.call_args.kwargs
        assert kwargs["snapshot_id"] == snapshot_id
        assert kwargs["extraction"].structured_data.brand == "TechCorp"
