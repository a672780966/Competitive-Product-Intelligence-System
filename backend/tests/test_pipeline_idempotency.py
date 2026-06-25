"""
CPIS V1 — 管道幂等性测试

Verifies that running the same collection URL twice does not create duplicate
SourceSnapshot, Product, or ProductVersion records, and that task status
transitions are idempotent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Base, CollectionTask, Product, ProductVersion, SourceSnapshot
from app.models.enums import TaskStatus
from app.collectors.base import CollectResult
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

SAME_URL = "https://example.com/techpro-x100"


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
# Stage: collect_url — snapshot idempotency
# ══════════════════════════════════════════════════════════════════


class TestCollectUrlIdempotent:
    @pytest.mark.asyncio
    async def test_two_tasks_same_url_no_duplicate_snapshot_per_task(
        self, db_session: AsyncSession,
    ) -> None:
        from app.tasks.collection import _do_collect

        task1 = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        task2 = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        db_session.add(task1)
        db_session.add(task2)
        await db_session.flush()

        fetch_result = CollectResult(
            success=True, final_url=SAME_URL, http_status=200,
            page_title="TechPro X100", raw_html=SAMPLE_HTML,
            content_hash="abc123def456", fetch_time_ms=150,
            used_playwright=False,
        )
        mock_cm = _mock_celery_session_cm(db_session)

        for task in (task1, task2):
            with (
                patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
                patch(
                    "app.tasks.collection._collector_selector.fetch",
                    new=AsyncMock(return_value=fetch_result),
                ),
                patch("app.tasks.collection.clean_content.delay"),
            ):
                result = await _do_collect(str(task.id), SAME_URL)
            assert result["status"] == "completed"

        for task in (task1, task2):
            count = await db_session.scalar(
                select(func.count(SourceSnapshot.id))
                .where(SourceSnapshot.task_id == task.id)
            )
            assert count == 1, f"Task {task.id} has {count} snapshots"

        total = await db_session.scalar(select(func.count(SourceSnapshot.id)))
        assert total == 2

    @pytest.mark.asyncio
    async def test_source_snapshot_unique_task_id_constraint(
        self, db_session: AsyncSession,
    ) -> None:
        task = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        snapshot1 = SourceSnapshot(
            task_id=task.id, final_url=SAME_URL,
            raw_html=SAMPLE_HTML, html_hash="abc123",
        )
        db_session.add(snapshot1)
        await db_session.commit()

        count_before = await db_session.scalar(
            select(func.count(SourceSnapshot.id))
            .where(SourceSnapshot.task_id == task.id)
        )
        assert count_before == 1

        snapshot2 = SourceSnapshot(
            task_id=task.id, final_url=SAME_URL,
            raw_html=SAMPLE_HTML, html_hash="def456",
        )
        db_session.add(snapshot2)
        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()


# ══════════════════════════════════════════════════════════════════
# Full pipeline — Product / ProductVersion idempotency
# ══════════════════════════════════════════════════════════════════


class TestFullPipelineIdempotent:
    @pytest.mark.asyncio
    async def test_two_tasks_same_url_produces_one_product(
        self, db_session: AsyncSession,
    ) -> None:
        from app.tasks.collection import _do_collect, _do_clean, _do_extract
        from app.extractors.product_extractor import ProductExtractor

        task1 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        task2 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        db_session.add(task1)
        db_session.add(task2)
        await db_session.flush()

        fetch_result = CollectResult(
            success=True, final_url=SAME_URL, http_status=200,
            page_title="TechPro X100", raw_html=SAMPLE_HTML,
            content_hash="abc123def456", fetch_time_ms=150,
            used_playwright=False,
        )
        clean_result = CleanResult(
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456", success=True,
        )
        extraction_result = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp", product_name="TechPro X100", model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )

        for task in (task1, task2):
            task_id = str(task.id)

            # collect
            with (
                patch("app.tasks.collection.get_celery_session",
                      return_value=_mock_celery_session_cm(db_session)),
                patch("app.tasks.collection._collector_selector.fetch",
                      new=AsyncMock(return_value=fetch_result)),
                patch("app.tasks.collection.clean_content.delay"),
            ):
                await _do_collect(task_id, SAME_URL)

            # clean
            with (
                patch("app.tasks.collection.get_celery_session",
                      return_value=_mock_celery_session_cm(db_session)),
                patch("app.tasks.collection._html_cleaner.clean",
                      return_value=clean_result),
                patch("app.tasks.collection.extract_structured_data.delay"),
            ):
                await _do_clean(task_id)

        # extract for task1 — real ProductVersioningService
        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            result1 = await _do_extract(str(task1.id))
        assert result1["status"] == "completed"

        # extract for task2 — real ProductVersioningService (same extraction)
        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            result2 = await _do_extract(str(task2.id))
        assert result2["status"] == "completed"

        assert result1["product_id"] == result2["product_id"]

        total_products = await db_session.scalar(
            select(func.count(Product.id))
        )
        assert total_products == 1

        total_versions = await db_session.scalar(
            select(func.count(ProductVersion.id))
        )
        assert total_versions == 1

    @pytest.mark.asyncio
    async def test_pipeline_twice_no_duplicate_product_version_via_real_service(
        self, db_session: AsyncSession,
    ) -> None:
        from app.tasks.collection import _do_collect, _do_clean, _do_extract
        from app.extractors.product_extractor import ProductExtractor

        task = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        fetch_result = CollectResult(
            success=True, final_url=SAME_URL, http_status=200,
            page_title="TechPro X100", raw_html=SAMPLE_HTML,
            content_hash="abc123def456", fetch_time_ms=150,
            used_playwright=False,
        )
        clean_result = CleanResult(
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456", success=True,
        )
        extraction_result = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp", product_name="TechPro X100", model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )
        extraction_result_v2 = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp", product_name="TechPro X100 v2", model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device — updated",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )

        task_id = str(task.id)

        # First run
        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._collector_selector.fetch",
                  new=AsyncMock(return_value=fetch_result)),
            patch("app.tasks.collection.clean_content.delay"),
        ):
            await _do_collect(task_id, SAME_URL)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._html_cleaner.clean",
                  return_value=clean_result),
            patch("app.tasks.collection.extract_structured_data.delay"),
        ):
            await _do_clean(task_id)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            result1 = await _do_extract(task_id)
        assert result1["status"] == "completed"

        assert await db_session.scalar(select(func.count(Product.id))) == 1
        assert await db_session.scalar(select(func.count(ProductVersion.id))) == 1

        # Second run — same URL, same content (no new version expected)
        # Create a second task for the same URL
        task2 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        db_session.add(task2)
        await db_session.flush()

        task_id2 = str(task2.id)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._collector_selector.fetch",
                  new=AsyncMock(return_value=fetch_result)),
            patch("app.tasks.collection.clean_content.delay"),
        ):
            await _do_collect(task_id2, SAME_URL)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._html_cleaner.clean",
                  return_value=clean_result),
            patch("app.tasks.collection.extract_structured_data.delay"),
        ):
            await _do_clean(task_id2)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            result2 = await _do_extract(task_id2)
        assert result2["status"] == "completed"
        assert result2["product_id"] == result1["product_id"]

        assert await db_session.scalar(select(func.count(Product.id))) == 1
        assert await db_session.scalar(select(func.count(ProductVersion.id))) == 1

        # Third run — different content, should create version 2 in same product
        task3 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        db_session.add(task3)
        await db_session.flush()

        task_id3 = str(task3.id)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._collector_selector.fetch",
                  new=AsyncMock(return_value=fetch_result)),
            patch("app.tasks.collection.clean_content.delay"),
        ):
            await _do_collect(task_id3, SAME_URL)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch("app.tasks.collection._html_cleaner.clean",
                  return_value=clean_result),
            patch("app.tasks.collection.extract_structured_data.delay"),
        ):
            await _do_clean(task_id3)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result_v2)),
        ):
            result3 = await _do_extract(task_id3)
        assert result3["status"] == "completed"
        assert result3["product_id"] == result1["product_id"]

        assert await db_session.scalar(select(func.count(Product.id))) == 1
        assert await db_session.scalar(select(func.count(ProductVersion.id))) == 2


# ══════════════════════════════════════════════════════════════════
# Mock DB session to track insert calls
# ══════════════════════════════════════════════════════════════════


class TestInsertTracking:
    @pytest.mark.asyncio
    async def test_tracks_insert_calls_no_duplicate_inserts(
        self, db_session: AsyncSession,
    ) -> None:
        from app.tasks.collection import _do_collect, _do_clean, _do_extract
        from app.extractors.product_extractor import ProductExtractor

        task1 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        task2 = CollectionTask(
            source_url=SAME_URL, domain="example.com",
            status=TaskStatus.PENDING, created_at=_now(), updated_at=_now(),
        )
        db_session.add(task1)
        db_session.add(task2)
        await db_session.flush()

        fetch_result = CollectResult(
            success=True, final_url=SAME_URL, http_status=200,
            page_title="TechPro X100", raw_html=SAMPLE_HTML,
            content_hash="abc123def456", fetch_time_ms=150,
            used_playwright=False,
        )
        clean_result = CleanResult(
            cleaned_text="TechPro X100 $299.99",
            cleaned_markdown="# TechPro X100",
            content_hash="def456", success=True,
        )
        extraction_result = ExtractionResult(
            structured_data=ProductFactFields(
                brand="TechCorp", product_name="TechPro X100", model="TP-X100",
            ),
            analysis_data=ProductAnalysisFields(
                analysis_summary="Premium EMS device",
            ),
            overall_confidence=0.85,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        )

        original_add = db_session.add
        insert_count = {"total": 0, "snapshot": 0, "product": 0, "version": 0}

        def counting_add(obj):
            insert_count["total"] += 1
            if isinstance(obj, SourceSnapshot):
                insert_count["snapshot"] += 1
            elif isinstance(obj, Product):
                insert_count["product"] += 1
            elif isinstance(obj, ProductVersion):
                insert_count["version"] += 1
            return original_add(obj)

        db_session.add = counting_add

        for task in (task1, task2):
            task_id = str(task.id)

            with (
                patch("app.tasks.collection.get_celery_session",
                      return_value=_mock_celery_session_cm(db_session)),
                patch("app.tasks.collection._collector_selector.fetch",
                      new=AsyncMock(return_value=fetch_result)),
                patch("app.tasks.collection.clean_content.delay"),
            ):
                await _do_collect(task_id, SAME_URL)

            with (
                patch("app.tasks.collection.get_celery_session",
                      return_value=_mock_celery_session_cm(db_session)),
                patch("app.tasks.collection._html_cleaner.clean",
                      return_value=clean_result),
                patch("app.tasks.collection.extract_structured_data.delay"),
            ):
                await _do_clean(task_id)

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            await _do_extract(str(task1.id))

        with (
            patch("app.tasks.collection.get_celery_session",
                  return_value=_mock_celery_session_cm(db_session)),
            patch.object(ProductExtractor, "extract",
                         new=AsyncMock(return_value=extraction_result)),
        ):
            await _do_extract(str(task2.id))

        assert insert_count["snapshot"] == 2
        assert insert_count["product"] == 1
        assert insert_count["version"] == 1


# ══════════════════════════════════════════════════════════════════
# Task status transition idempotency
# ══════════════════════════════════════════════════════════════════


class TestStatusTransitionsIdempotent:
    @pytest.mark.asyncio
    async def test_update_status_same_status_multiple_times(
        self, db_session: AsyncSession,
    ) -> None:
        from app.repositories.task_repository import TaskRepository

        task = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        repo = TaskRepository(db_session)

        for _ in range(3):
            updated = await repo.update_status(task.id, TaskStatus.FETCHING)
            assert updated is not None

        await db_session.refresh(task)
        assert task.status == TaskStatus.FETCHING.value

    @pytest.mark.asyncio
    async def test_update_status_twice_same_value_no_error(
        self, db_session: AsyncSession,
    ) -> None:
        from app.repositories.task_repository import TaskRepository

        task = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        repo = TaskRepository(db_session)
        updated = await repo.update_status(task.id, TaskStatus.COMPLETED)
        assert updated is not None
        await db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value

        updated2 = await repo.update_status(task.id, TaskStatus.COMPLETED)
        assert updated2 is not None
        await db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_status_transitions_in_pipeline_stages_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        from app.tasks.collection import _do_collect
        from app.repositories.task_repository import TaskRepository

        task = CollectionTask(
            source_url=SAME_URL, status=TaskStatus.PENDING,
            created_at=_now(), updated_at=_now(),
        )
        db_session.add(task)
        await db_session.flush()

        fetch_result = CollectResult(
            success=True, final_url=SAME_URL, http_status=200,
            page_title="TechPro X100", raw_html=SAMPLE_HTML,
            content_hash="abc123def456", fetch_time_ms=150,
            used_playwright=False,
        )

        mock_cm = _mock_celery_session_cm(db_session)
        with (
            patch("app.tasks.collection.get_celery_session", return_value=mock_cm),
            patch(
                "app.tasks.collection._collector_selector.fetch",
                new=AsyncMock(return_value=fetch_result),
            ),
            patch("app.tasks.collection.clean_content.delay"),
        ):
            result = await _do_collect(str(task.id), SAME_URL)
        assert result["status"] == "completed"

        repo = TaskRepository(db_session)
        for _ in range(3):
            updated = await repo.update_status(task.id, TaskStatus.COMPLETED)
            assert updated is not None

        await db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value
