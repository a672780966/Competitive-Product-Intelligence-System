"""
CPIS V1 — 采集任务 API & Service 集成测试

Uses an in-memory SQLite database via dependency override.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base

client = TestClient(app)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a fresh SQLite in-memory database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        poolclass=NullPool,
    )
    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)

    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency to use our test database."""

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════
# Task Service Tests (Unit)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestTaskService:
    async def test_create_and_get_task(self, db_session: AsyncSession):
        from app.schemas.task import CreateTaskRequest
        from app.services.task_service import TaskService

        service = TaskService(db_session)
        req = CreateTaskRequest(source_url="https://example.com/product")
        task_resp = await service.create_task(req)

        assert task_resp.id is not None
        assert task_resp.source_url == "https://example.com/product"
        assert task_resp.status in ("pending", "validating", "blocked")  # validation runs

        # Get task detail
        detail = await service.get_task(task_resp.id)
        assert detail is not None
        assert detail.source_url == task_resp.source_url

    async def test_list_tasks(self, db_session: AsyncSession):
        from app.schemas.task import CreateTaskRequest, TaskListQuery
        from app.services.task_service import TaskService

        service = TaskService(db_session)
        await service.create_task(CreateTaskRequest(source_url="https://example.com/p1"))
        await service.create_task(CreateTaskRequest(source_url="https://example.com/p2"))

        result = await service.list_tasks(TaskListQuery(page=1, page_size=20))
        assert result.total == 2
        assert len(result.items) == 2

    async def test_cancel_task(self, db_session: AsyncSession):
        from app.schemas.task import CreateTaskRequest
        from app.services.task_service import TaskService

        service = TaskService(db_session)
        task = await service.create_task(CreateTaskRequest(source_url="https://example.com/p"))

        # After creation, task might be pending or blocked due to URL validation
        detail = await service.cancel_task(task.id)
        assert detail is not None
        assert detail.status == "cancelled"

    async def test_get_events(self, db_session: AsyncSession):
        from app.schemas.task import CreateTaskRequest
        from app.services.task_service import TaskService

        service = TaskService(db_session)
        task = await service.create_task(CreateTaskRequest(source_url="https://example.com/p"))

        events = await service.get_events(task.id)
        assert events is not None
        assert len(events) >= 1  # At least "creation" event
        assert events[0].stage == "creation"

    async def test_retry_blocked_task(self, db_session: AsyncSession):
        from app.schemas.task import CreateTaskRequest
        from app.services.task_service import TaskService

        service = TaskService(db_session)
        # localhost URL will be blocked by URL validation
        task = await service.create_task(CreateTaskRequest(source_url="http://localhost/admin"))

        detail = await service.retry_task(task.id)
        # retry should work on a blocked task
        assert detail is not None
        assert detail.retry_count >= 1


# ══════════════════════════════════════════════════════════════════
# Schema Validation Tests
# ══════════════════════════════════════════════════════════════════


class TestApiSchemaValidation:
    def test_create_task_request_validates(self):
        from app.schemas.task import CreateTaskRequest

        r = CreateTaskRequest(source_url="https://example.com/p")
        assert r.source_url == "https://example.com/p"

    def test_create_task_request_rejects_empty_url(self):
        from pydantic import ValidationError
        from app.schemas.task import CreateTaskRequest

        with pytest.raises(ValidationError):
            CreateTaskRequest(source_url="")

    def test_batch_request_validates(self):
        from app.schemas.task import BatchCreateTaskRequest

        r = BatchCreateTaskRequest(tasks=[
            {"source_url": "https://example.com/p1"},
            {"source_url": "https://example.com/p2"},
        ])
        assert len(r.tasks) == 2

    def test_batch_request_rejects_empty(self):
        from pydantic import ValidationError
        from app.schemas.task import BatchCreateTaskRequest

        with pytest.raises(ValidationError):
            BatchCreateTaskRequest(tasks=[])

    def test_task_response_with_optional_fields(self):
        from app.schemas.task import TaskResponse

        r = TaskResponse(
            id="00000000-0000-0000-0000-000000000001",
            source_url="https://example.com/p",
            status="pending",
            priority=50,
            auto_sync_feishu=False,
            retry_count=0,
            max_retries=3,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert r.normalized_url is None  # Optional field
        assert r.category_hint is None

    def test_task_detail_response_with_events(self):
        from app.schemas.task import TaskDetailResponse

        r = TaskDetailResponse(
            id="00000000-0000-0000-0000-000000000001",
            source_url="https://example.com/p",
            status="completed",
            priority=50,
            auto_sync_feishu=False,
            retry_count=0,
            max_retries=3,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert r.events == []  # Default empty list


# ══════════════════════════════════════════════════════════════════
# API Integration Tests (with real DB)
# ══════════════════════════════════════════════════════════════════


class TestTaskApiIntegration:
    """End-to-end API tests using overridden DB dependency."""

    async def test_get_task_detail_with_snapshot(self, override_get_db, db_session: AsyncSession):
        from app.models import CollectionTask, SourceSnapshot
        from app.models.enums import TaskStatus

        task = CollectionTask(
            source_url="https://example.com/snapshot-detail",
            status=TaskStatus.COMPLETED.value,
            priority=50,
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/snapshot-detail",
            html_hash="html-hash",
            content_hash="content-hash",
            cleaned_text="Cleaned text",
            cleaned_markdown="# Cleaned text",
        )
        db_session.add(snapshot)
        await db_session.flush()

        resp = client.get(f"/api/v1/collection-tasks/{task.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot"]["id"] == str(snapshot.id)
        assert data["snapshot"]["task_id"] == str(task.id)
        assert data["snapshot"]["final_url"] == "https://example.com/snapshot-detail"
        assert data["snapshot"]["content_hash"] == "content-hash"
        assert data["snapshot"]["cleaned_text"] == "Cleaned text"

    async def test_get_task_snapshot(self, override_get_db, db_session: AsyncSession):
        from app.models import CollectionTask, SourceSnapshot
        from app.models.enums import TaskStatus

        task = CollectionTask(
            source_url="https://example.com/snapshot-endpoint",
            status=TaskStatus.COMPLETED.value,
            priority=50,
        )
        db_session.add(task)
        await db_session.flush()

        snapshot = SourceSnapshot(
            task_id=task.id,
            final_url="https://example.com/snapshot-endpoint",
            html_hash="endpoint-html-hash",
            content_hash="endpoint-content-hash",
            cleaned_text="Endpoint cleaned text",
            cleaned_markdown="Endpoint cleaned markdown",
        )
        db_session.add(snapshot)
        await db_session.flush()

        resp = client.get(f"/api/v1/collection-tasks/{task.id}/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(snapshot.id)
        assert data["task_id"] == str(task.id)
        assert data["html_hash"] == "endpoint-html-hash"
        assert data["cleaned_markdown"] == "Endpoint cleaned markdown"

    async def test_get_task_snapshot_not_found(self, override_get_db, db_session: AsyncSession):
        from app.models import CollectionTask
        from app.models.enums import TaskStatus

        task = CollectionTask(
            source_url="https://example.com/no-snapshot",
            status=TaskStatus.PENDING.value,
            priority=50,
        )
        db_session.add(task)
        await db_session.flush()

        resp = client.get(f"/api/v1/collection-tasks/{task.id}/snapshots")
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_pipeline_status_in_detail(self, override_get_db, db_session: AsyncSession):
        from app.models import CollectionTask, TaskEvent
        from app.models.enums import TaskStatus

        task = CollectionTask(
            source_url="https://example.com/pipeline-status",
            status=TaskStatus.FAILED.value,
            priority=50,
            retry_count=1,
            max_retries=3,
        )
        db_session.add(task)
        await db_session.flush()

        db_session.add_all([
            TaskEvent(
                task_id=task.id,
                stage="validation",
                status=TaskStatus.PENDING.value,
                message="Starting validation",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            TaskEvent(
                task_id=task.id,
                stage="validation",
                status=TaskStatus.FAILED.value,
                message="Validation failed",
                error_code="VALIDATION_ERROR",
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            ),
            TaskEvent(
                task_id=task.id,
                stage="retry",
                status=TaskStatus.PENDING.value,
                message="Retry attempt 1",
                created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
            ),
        ])
        await db_session.flush()

        resp = client.get(f"/api/v1/collection-tasks/{task.id}")
        assert resp.status_code == 200
        pipeline_status = resp.json()["pipeline_status"]
        assert pipeline_status["overall_status"] == "failed"
        assert pipeline_status["current_stage"] == "retry"
        assert pipeline_status["retry_count"] == 1
        assert pipeline_status["max_retries"] == 3
        assert pipeline_status["stages"] == [
            {
                "stage": "validation",
                "status": "failed",
                "error_code": "VALIDATION_ERROR",
                "error_message": "Validation failed",
            },
            {
                "stage": "retry",
                "status": "pending",
                "error_code": None,
                "error_message": None,
            },
        ]

    def test_create_task(self, override_get_db):
        resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/product",
            "category_hint": "smartphone",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_url"] == "https://example.com/product"
        assert data["category_hint"] == "smartphone"
        assert "id" in data

    def test_batch_create(self, override_get_db):
        resp = client.post("/api/v1/collection-tasks/batch", json={
            "tasks": [
                {"source_url": "https://example.com/p1"},
                {"source_url": "https://example.com/p2"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] == 2
        assert len(data["tasks"]) == 2

    def test_list_and_filter(self, override_get_db):
        # Create a task first
        client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/test-product",
            "category_hint": "laptop",
        })

        resp = client.get("/api/v1/collection-tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        # Filter by keyword
        resp = client.get("/api/v1/collection-tasks?keyword=test-product")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_task_detail(self, override_get_db):
        create_resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/detail-test",
        })
        task_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/collection-tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["source_url"] == "https://example.com/detail-test"

    def test_get_task_not_found(self, override_get_db):
        resp = client.get(f"/api/v1/collection-tasks/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_invalid_uuid_returns_422(self, override_get_db):
        resp = client.get("/api/v1/collection-tasks/not-a-uuid")
        assert resp.status_code == 422

    def test_retry_task(self, override_get_db):
        # Create a blocked task (localhost will be blocked by URL validation)
        create_resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "http://localhost/admin",
        })
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/collection-tasks/{task_id}/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["retry_count"] >= 1

    def test_cancel_task(self, override_get_db):
        create_resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/cancel-me",
        })
        task_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/collection-tasks/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_get_task_events(self, override_get_db):
        create_resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/event-test",
        })
        task_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/collection-tasks/{task_id}/events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert events[0]["stage"] == "creation"
