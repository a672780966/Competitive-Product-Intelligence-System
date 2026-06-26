"""Tests for Node 6 — ScheduledCollection API.

Tests the scheduled collection endpoints and ScheduleManager.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base, CollectionTemplate, ScheduledCollection
from app.models.enums import CollectionTemplateStatus, ScheduleType

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


@pytest.fixture
async def sample_template(db_session: AsyncSession) -> CollectionTemplate:
    """Create a sample template."""
    template = CollectionTemplate(
        name="Schedule Test Template",
        description="For scheduling tests",
        source_plan={
            "sources": [
                {"title": "Test", "url": "https://example.com", "domain": "example.com"},
            ],
        },
        run_plan={
            "version": "1.0",
            "name": "Schedule Test",
            "sources": [
                {"type": "url_list", "urls": ["https://example.com"]},
            ],
        },
        status=CollectionTemplateStatus.ACTIVE,
    )
    db_session.add(template)
    await db_session.flush()
    return template


@pytest.fixture
async def sample_schedule(db_session: AsyncSession, sample_template) -> ScheduledCollection:
    """Create a sample schedule."""
    schedule = ScheduledCollection(
        template_id=sample_template.id,
        schedule_type=ScheduleType.DAILY,
        enabled=True,
    )
    db_session.add(schedule)
    await db_session.flush()
    return schedule


# ══════════════════════════════════════════════════════════════════
# ScheduleManager Tests
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestScheduleManager:
    """Tests for ScheduleManager."""

    async def test_create_schedule_daily(self, db_session: AsyncSession, sample_template):
        """Should create a daily schedule."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.DAILY,
        )
        result = await manager.create_schedule(req)
        assert result is not None
        assert result.template_id == sample_template.id
        assert result.schedule_type == "daily"
        assert result.enabled is True

    async def test_create_schedule_cron(self, db_session: AsyncSession, sample_template):
        """Should create a cron schedule."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.CRON,
            cron_expr="0 6 * * *",
        )
        result = await manager.create_schedule(req)
        assert result is not None
        assert result.cron_expr == "0 6 * * *"
        assert result.next_run_at is not None

    async def test_create_schedule_interval(self, db_session: AsyncSession, sample_template):
        """Should create an interval schedule."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=60,
        )
        result = await manager.create_schedule(req)
        assert result is not None
        assert result.interval_minutes == 60

    async def test_create_schedule_template_not_found(self, db_session: AsyncSession):
        """Should return None when template doesn't exist."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=uuid.uuid4(),
            schedule_type=ScheduleType.DAILY,
        )
        result = await manager.create_schedule(req)
        assert result is None

    async def test_list_schedules(self, db_session: AsyncSession, sample_template):
        """Should list schedules."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.DAILY,
        )
        await manager.create_schedule(req)

        result = await manager.list_schedules()
        assert result.total >= 1

    async def test_get_schedule(self, db_session: AsyncSession, sample_schedule):
        """Should get a schedule by ID."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        result = await manager.get_schedule(sample_schedule.id)
        assert result is not None
        assert result.id == sample_schedule.id

    async def test_get_schedule_not_found(self, db_session: AsyncSession):
        """Should return None for non-existent schedule."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        result = await manager.get_schedule(uuid.uuid4())
        assert result is None

    async def test_get_schedule_detail(self, db_session: AsyncSession, sample_schedule):
        """Should get schedule with template info."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        detail = await manager.get_schedule_detail(sample_schedule.id)
        assert detail is not None
        assert detail.template is not None
        assert detail.template.name == "Schedule Test Template"

    async def test_update_schedule_enable(self, db_session: AsyncSession, sample_template):
        """Should update schedule enabled status."""
        from app.schemas.template_schedule import (
            ScheduledCollectionCreateRequest,
            ScheduledCollectionUpdateRequest,
        )
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.DAILY,
            enabled=False,
        )
        created = await manager.create_schedule(req)
        assert created.enabled is False

        updated = await manager.update_schedule(
            created.id,
            ScheduledCollectionUpdateRequest(enabled=True),
        )
        assert updated is not None
        assert updated.enabled is True

    async def test_update_schedule_not_found(self, db_session: AsyncSession):
        """Should return None when updating non-existent schedule."""
        from app.schemas.template_schedule import ScheduledCollectionUpdateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        result = await manager.update_schedule(
            uuid.uuid4(),
            ScheduledCollectionUpdateRequest(enabled=True),
        )
        assert result is None

    async def test_execute_schedule(self, db_session: AsyncSession, sample_schedule):
        """Should execute a schedule and update state."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)

        with patch.object(
            manager._template_service, "run_template", new_callable=AsyncMock,
        ) as mock_run:
            from app.schemas.template_schedule import TemplateRunResponse

            mock_run.return_value = TemplateRunResponse(
                template_id=sample_schedule.template_id,
                tasks_created=2,
                message="OK",
            )

            result = await manager.execute_schedule(sample_schedule.id)
            assert result["status"] == "completed"
            assert result["tasks_created"] == 2

    async def test_execute_schedule_disabled(self, db_session: AsyncSession, sample_template):
        """Should skip disabled schedules."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.DAILY,
            enabled=False,
        )
        created = await manager.create_schedule(req)

        result = await manager.execute_schedule(created.id)
        assert result["status"] == "skipped"

    async def test_execute_schedule_failure_tracking(self, db_session: AsyncSession, sample_template):
        """Should increment failure count on error."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.DAILY,
            max_failures_before_pause=2,
        )
        created = await manager.create_schedule(req)

        with patch.object(
            manager._template_service, "run_template", new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Test failure")

            result = await manager.execute_schedule(created.id)
            assert result["status"] == "failed"
            assert result["failure_count"] == 1

            result2 = await manager.execute_schedule(created.id)
            assert result2["status"] == "failed"
            assert result2["failure_count"] == 2

            # Auto-paused after max failures
            updated = await manager.get_schedule(created.id)
            assert updated is not None
            assert updated.enabled is False

    async def test_execute_due_schedules(self, db_session: AsyncSession, sample_template):
        """Should find and execute due schedules."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)

        req = ScheduledCollectionCreateRequest(
            template_id=sample_template.id,
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=60,
        )
        created = await manager.create_schedule(req)

        # Manually set next_run_at in the past
        stmt = (
            sa_update(ScheduledCollection)
            .where(ScheduledCollection.id == created.id)
            .values(next_run_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        )
        await db_session.execute(stmt)

        with patch.object(
            manager._template_service, "run_template", new_callable=AsyncMock,
        ) as mock_run:
            from app.schemas.template_schedule import TemplateRunResponse

            mock_run.return_value = TemplateRunResponse(
                template_id=sample_template.id,
                tasks_created=1,
                message="OK",
            )

            results = await manager.execute_due_schedules()
            assert len(results) >= 1
            assert results[0]["status"] == "completed"


# ══════════════════════════════════════════════════════════════════
# Schedule API Tests
# ══════════════════════════════════════════════════════════════════


class TestScheduledCollectionAPI:
    """Tests for scheduled collection API endpoints."""

    def test_list_schedules_empty(self, override_get_db):
        """GET /api/v1/scheduled-collections should return empty list."""
        resp = client.get("/api/v1/scheduled-collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_create_schedule(self, override_get_db, db_session: AsyncSession, sample_template):
        """POST /api/v1/scheduled-collections should create schedule."""
        resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "daily",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["template_id"] == str(sample_template.id)
        assert data["schedule_type"] == "daily"
        assert data["enabled"] is True

    def test_create_schedule_template_not_found(self, override_get_db):
        """POST with non-existent template should 404."""
        resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(uuid.uuid4()),
                "schedule_type": "daily",
            },
        )
        assert resp.status_code == 404

    def test_create_schedule_with_cron(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should create schedule with cron expression."""
        resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "cron",
                "cron_expr": "0 6 * * *",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["cron_expr"] == "0 6 * * *"
        assert data["next_run_at"] is not None

    def test_create_schedule_with_interval(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should create schedule with interval."""
        resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "interval",
                "interval_minutes": 120,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["interval_minutes"] == 120

    def test_create_then_get_schedule(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should create then retrieve schedule."""
        # Create schedule via API
        create_resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "daily",
            },
        )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["id"]

        # Get schedule
        resp = client.get(f"/api/v1/scheduled-collections/{schedule_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["schedule"]["id"] == schedule_id
        assert data["template"] is not None
        assert data["template"]["name"] == "Schedule Test Template"

    def test_get_schedule_not_found(self, override_get_db):
        """GET non-existent schedule should 404."""
        resp = client.get(f"/api/v1/scheduled-collections/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_patch_schedule(self, override_get_db, db_session: AsyncSession, sample_template):
        """PATCH /api/v1/scheduled-collections/{id} should update."""
        # Create first
        create_resp = client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "daily",
            },
        )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/scheduled-collections/{schedule_id}",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False

    def test_patch_schedule_not_found(self, override_get_db):
        """PATCH non-existent schedule should 404."""
        resp = client.patch(
            f"/api/v1/scheduled-collections/{uuid.uuid4()}",
            json={"enabled": True},
        )
        assert resp.status_code == 404

    def test_list_schedules_filter_enabled(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should filter schedules by enabled status."""
        # Create enabled schedule
        client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "daily",
                "enabled": True,
            },
        )
        # Create disabled schedule
        client.post(
            "/api/v1/scheduled-collections",
            json={
                "template_id": str(sample_template.id),
                "schedule_type": "daily",
                "enabled": False,
            },
        )

        resp = client.get("/api/v1/scheduled-collections?enabled=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        resp = client.get("/api/v1/scheduled-collections?enabled=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


# ══════════════════════════════════════════════════════════════════
# Schedule Schema Tests
# ══════════════════════════════════════════════════════════════════


class TestScheduleSchemas:
    """Tests for schedule Pydantic schemas."""

    def test_create_request_valid(self):
        """Should validate create request."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest

        req = ScheduledCollectionCreateRequest(
            template_id=uuid.uuid4(),
            schedule_type=ScheduleType.DAILY,
        )
        assert req.enabled is True
        assert req.max_failures_before_pause == 3

    def test_create_request_with_cron(self):
        """Should accept cron expression."""
        from app.schemas.template_schedule import ScheduledCollectionCreateRequest

        req = ScheduledCollectionCreateRequest(
            template_id=uuid.uuid4(),
            schedule_type=ScheduleType.CRON,
            cron_expr="0 6 * * *",
        )
        assert req.cron_expr == "0 6 * * *"

    def test_update_request_partial(self):
        """Should allow partial updates."""
        from app.schemas.template_schedule import ScheduledCollectionUpdateRequest

        req = ScheduledCollectionUpdateRequest(enabled=False)
        assert req.enabled is False
        assert req.schedule_type is None

    def test_schedule_response_from_attributes(self):
        """ScheduledCollectionResponse should support from_attributes."""
        from app.schemas.template_schedule import ScheduledCollectionResponse

        # Verify model_config has from_attributes
        assert ScheduledCollectionResponse.model_config.get("from_attributes") is True
        assert "id" in ScheduledCollectionResponse.model_fields
        assert "enabled" in ScheduledCollectionResponse.model_fields


# ══════════════════════════════════════════════════════════════════
# Schedule Manager Edge Cases
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestScheduleManagerEdgeCases:
    """Edge cases for ScheduleManager."""

    async def test_calculate_next_run_cron(self):
        """Should calculate next run from cron expression."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "cron",
            cron_expr="0 6 * * *",
            from_time=now,
        )
        assert next_run is not None
        assert next_run > now
        assert next_run.hour == 6
        assert next_run.minute == 0

    async def test_calculate_next_run_interval(self):
        """Should calculate next run from interval."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "interval",
            interval_minutes=60,
            from_time=now,
        )
        assert next_run is not None
        assert next_run > now
        assert (next_run - now).total_seconds() == 3600  # 60 minutes

    async def test_calculate_next_run_daily(self):
        """Should calculate next run for daily."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "daily",
            from_time=now,
        )
        assert next_run is not None
        assert (next_run - now).days == 1

    async def test_calculate_next_run_weekly(self):
        """Should calculate next run for weekly."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "weekly",
            from_time=now,
        )
        assert next_run is not None
        assert (next_run - now).days == 7

    async def test_list_schedules_pagination(self, db_session: AsyncSession, sample_template):
        """Should paginate schedules."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)

        # Create several schedules
        for i in range(3):
            schedule = ScheduledCollection(
                template_id=sample_template.id,
                schedule_type=ScheduleType.DAILY,
                enabled=True,
            )
            db_session.add(schedule)
        await db_session.flush()

        result = await manager.list_schedules(page=1, page_size=2)
        assert result.total >= 3
        assert len(result.items) == 2

    async def test_execute_schedule_not_found(self, db_session: AsyncSession):
        """Should handle non-existent schedule execution."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager(db_session)
        result = await manager.execute_schedule(uuid.uuid4())
        assert result["status"] == "failed"
        assert "not found" in result["error"]

    async def test_calculate_next_run_cron_invalid(self):
        """Should handle invalid cron expression gracefully."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "cron",
            cron_expr="invalid-cron",
            from_time=now,
        )
        assert next_run is None  # Invalid cron returns None

    async def test_calculate_next_run_no_params(self):
        """Should default to daily when no specific params given."""
        from app.services.schedule_manager import ScheduleManager

        manager = ScheduleManager.__new__(ScheduleManager)
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        next_run = manager._calculate_next_run(
            "unknown_type",
            from_time=now,
        )
        assert next_run is not None
        # Default is daily
        assert (next_run - now).days == 1
