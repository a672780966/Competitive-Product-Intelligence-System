"""Tests for Node 7 — Usage API endpoints.

Tests the usage API endpoints and UsageService directly.
Uses SQLite in-memory database and mock provider pattern.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base, UsageDailyStat
from app.repositories.usage_repository import UsageRepository
from app.schemas.usage import (
    UsageDailyStatListResponse,
    UsageDailyStatResponse,
    UsageSummaryResponse,
)
from app.services.usage_service import UsageService

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
# Service Tests
# ══════════════════════════════════════════════════════════════════


class TestUsageService:
    """Direct service-level tests for UsageService."""

    @pytest.mark.asyncio
    async def test_record_usage_creates_new(self, db_session: AsyncSession):
        service = UsageService(db_session)
        result = await service.record_usage(
            task_count=5,
            token_count=1000,
            search_count=2,
            collected_page_count=10,
            success_count=4,
            failure_count=1,
            estimated_cost=0.05,
            stat_date=date(2025, 6, 1),
        )
        assert result.stat_date == date(2025, 6, 1)
        assert result.task_count == 5
        assert result.token_count == 1000
        assert result.search_count == 2
        assert result.collected_page_count == 10
        assert result.success_count == 4
        assert result.failure_count == 1
        assert result.estimated_cost == 0.05

    @pytest.mark.asyncio
    async def test_record_usage_accumulates(self, db_session: AsyncSession):
        service = UsageService(db_session)
        await service.record_usage(task_count=3, stat_date=date(2025, 6, 1))
        await service.record_usage(task_count=7, stat_date=date(2025, 6, 1))
        result = await service.record_usage(
            task_count=0, stat_date=date(2025, 6, 1),
        )
        assert result.task_count == 10  # 3 + 7 + 0

    @pytest.mark.asyncio
    async def test_record_usage_defaults_today(self, db_session: AsyncSession):
        service = UsageService(db_session)
        result = await service.record_usage(task_count=1)
        assert result.stat_date == date.today()
        assert result.task_count == 1

    @pytest.mark.asyncio
    async def test_get_daily_stats_default_range(self, db_session: AsyncSession):
        service = UsageService(db_session)
        # Record usage 40 days ago (outside default 30-day window)
        await service.record_usage(
            task_count=10, stat_date=date.today() - timedelta(days=40),
        )
        # Record usage today (inside default window)
        await service.record_usage(
            task_count=5, stat_date=date.today(),
        )

        result = await service.get_daily_stats()
        # Only today's record should be in the default 30-day window
        assert result.total >= 1
        today_stats = [s for s in result.items if s.stat_date == date.today()]
        assert len(today_stats) == 1
        assert today_stats[0].task_count == 5

    @pytest.mark.asyncio
    async def test_get_daily_stats_with_date_range(self, db_session: AsyncSession):
        service = UsageService(db_session)
        await service.record_usage(
            task_count=1, stat_date=date(2025, 6, 1),
        )
        await service.record_usage(
            task_count=2, stat_date=date(2025, 6, 2),
        )
        await service.record_usage(
            task_count=3, stat_date=date(2025, 6, 3),
        )

        result = await service.get_daily_stats(
            date_from=date(2025, 6, 1),
            date_to=date(2025, 6, 2),
        )
        assert result.total == 2
        dates = [s.stat_date for s in result.items]
        assert date(2025, 6, 1) in dates
        assert date(2025, 6, 2) in dates
        assert date(2025, 6, 3) not in dates

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, db_session: AsyncSession):
        service = UsageService(db_session)
        result = await service.get_summary()
        assert result.total_task_count == 0
        assert result.total_token_count == 0
        assert result.total_search_count == 0
        assert result.total_days == 0
        assert result.total_estimated_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_summary_with_data(self, db_session: AsyncSession):
        service = UsageService(db_session)
        await service.record_usage(
            task_count=5, token_count=1000, search_count=2,
            collected_page_count=10, success_count=4, failure_count=1,
            estimated_cost=0.05, stat_date=date(2025, 6, 1),
        )
        await service.record_usage(
            task_count=3, token_count=500, search_count=1,
            collected_page_count=5, success_count=3, failure_count=0,
            estimated_cost=0.03, stat_date=date(2025, 6, 2),
        )

        result = await service.get_summary()
        assert result.total_task_count == 8
        assert result.total_token_count == 1500
        assert result.total_search_count == 3
        assert result.total_collected_page_count == 15
        assert result.total_success_count == 7
        assert result.total_failure_count == 1
        assert abs(result.total_estimated_cost - 0.08) < 0.001
        assert result.total_days == 2


# ══════════════════════════════════════════════════════════════════
# Repository Tests
# ══════════════════════════════════════════════════════════════════


class TestUsageRepository:
    """Direct repository-level tests for UsageRepository."""

    @pytest.mark.asyncio
    async def test_upsert_creates(self, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        stat = await repo.upsert_daily_stat(
            date(2025, 6, 1),
            task_count=1, token_count=100, search_count=2,
        )
        assert stat.task_count == 1
        assert stat.token_count == 100

    @pytest.mark.asyncio
    async def test_upsert_accumulates(self, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        await repo.upsert_daily_stat(date(2025, 6, 1), task_count=5)
        stat = await repo.upsert_daily_stat(date(2025, 6, 1), task_count=3)
        assert stat.task_count == 8

    @pytest.mark.asyncio
    async def test_get_by_date(self, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        await repo.upsert_daily_stat(date(2025, 6, 1), task_count=1)
        stat = await repo.get_by_date(date(2025, 6, 1))
        assert stat is not None
        assert stat.task_count == 1
        not_found = await repo.get_by_date(date(2025, 6, 2))
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_daily_stats(self, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        await repo.upsert_daily_stat(date(2025, 6, 1), task_count=1)
        await repo.upsert_daily_stat(date(2025, 6, 2), task_count=2)
        await repo.upsert_daily_stat(date(2025, 6, 3), task_count=3)

        stats = await repo.get_daily_stats(date(2025, 6, 1), date(2025, 6, 2))
        assert len(stats) == 2
        assert stats[0].stat_date == date(2025, 6, 1)
        assert stats[1].stat_date == date(2025, 6, 2)

    @pytest.mark.asyncio
    async def test_get_summary_filtered(self, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        await repo.upsert_daily_stat(date(2025, 1, 1), task_count=10)
        await repo.upsert_daily_stat(date(2025, 6, 1), task_count=20)
        await repo.upsert_daily_stat(date(2025, 12, 1), task_count=30)

        summary = await repo.get_summary(
            date_from=date(2025, 6, 1), date_to=date(2025, 12, 31),
        )
        assert summary["total_task_count"] == 50
        assert summary["total_days"] == 2


# ══════════════════════════════════════════════════════════════════
# API Tests
# ══════════════════════════════════════════════════════════════════


def seed_usage_data(db_session: AsyncSession) -> None:
    """Helper to seed test data via the repository."""
    import asyncio
    repo = UsageRepository(db_session)
    asyncio.run(repo.upsert_daily_stat(
        date(2025, 6, 1), task_count=5, token_count=1000,
        search_count=2, collected_page_count=10,
        success_count=4, failure_count=1, estimated_cost=0.05,
    ))
    asyncio.run(repo.upsert_daily_stat(
        date(2025, 6, 2), task_count=3, token_count=500,
        search_count=1, collected_page_count=5,
        success_count=3, failure_count=0, estimated_cost=0.03,
    ))


class TestGetDailyStats:
    """GET /api/v1/usage/daily"""

    def test_empty_db_returns_empty_list(self, override_get_db):
        resp = client.get("/api/v1/usage/daily")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_daily_stats_with_data(self, override_get_db, db_session: AsyncSession):
        # Seed data
        repo = UsageRepository(db_session)
        import asyncio
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 1), task_count=5))
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 2), task_count=3))

        resp = client.get(
            "/api/v1/usage/daily?date_from=2025-06-01&date_to=2025-06-02",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["task_count"] == 5
        assert data["items"][1]["task_count"] == 3

    def test_daily_stats_date_filter(self, override_get_db, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        import asyncio
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 1), task_count=5))
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 2), task_count=3))

        resp = client.get(
            "/api/v1/usage/daily?date_from=2025-06-02&date_to=2025-06-02",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["stat_date"] == "2025-06-02"

    def test_daily_stats_no_date_filters_defaults(self, override_get_db):
        """Default range should not error."""
        resp = client.get("/api/v1/usage/daily")
        assert resp.status_code == 200

    def test_daily_stats_invalid_date(self, override_get_db):
        resp = client.get("/api/v1/usage/daily?date_from=invalid")
        assert resp.status_code == 422


class TestGetSummary:
    """GET /api/v1/usage/summary"""

    def test_summary_empty_db(self, override_get_db):
        resp = client.get("/api/v1/usage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_task_count"] == 0
        assert data["total_days"] == 0

    def test_summary_with_data(self, override_get_db, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        import asyncio
        asyncio.run(repo.upsert_daily_stat(
            date(2025, 6, 1),
            task_count=5, token_count=1000, search_count=2,
            collected_page_count=10, success_count=4, failure_count=1,
            estimated_cost=0.05,
        ))
        asyncio.run(repo.upsert_daily_stat(
            date(2025, 6, 2),
            task_count=3, token_count=500, search_count=1,
            collected_page_count=5, success_count=3, failure_count=0,
            estimated_cost=0.03,
        ))

        resp = client.get("/api/v1/usage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_task_count"] == 8
        assert data["total_token_count"] == 1500
        assert data["total_search_count"] == 3
        assert data["total_collected_page_count"] == 15
        assert data["total_success_count"] == 7
        assert data["total_failure_count"] == 1
        assert abs(data["total_estimated_cost"] - 0.08) < 0.001
        assert data["total_days"] == 2

    def test_summary_with_date_filter(self, override_get_db, db_session: AsyncSession):
        repo = UsageRepository(db_session)
        import asyncio
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 1), task_count=10))
        asyncio.run(repo.upsert_daily_stat(date(2025, 6, 2), task_count=20))

        resp = client.get(
            "/api/v1/usage/summary?date_from=2025-06-01&date_to=2025-06-01",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_task_count"] == 10
        assert data["total_days"] == 1

    def test_summary_response_has_all_fields(self, override_get_db):
        resp = client.get("/api/v1/usage/summary")
        data = resp.json()
        expected_fields = [
            "total_task_count", "total_token_count", "total_search_count",
            "total_collected_page_count", "total_success_count",
            "total_failure_count", "total_estimated_cost", "total_days",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
