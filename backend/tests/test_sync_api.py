"""
CPIS V1 - Sync Record API integration tests.

Uses an in-memory SQLite database via dependency override.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base, FeishuSyncRecord, Product
from app.models.enums import SyncStatus

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


async def create_product(
    db_session: AsyncSession,
    *,
    unique_key: str = "example.com/test-brand/test-model",
) -> Product:
    product = Product(
        unique_key=unique_key,
        brand="TestBrand",
        name="Test Product",
        model="TM-100",
        category="smartphone",
        review_status="pending",
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product


async def create_sync_record(
    db_session: AsyncSession,
    product: Product,
    *,
    sync_status: SyncStatus = SyncStatus.PENDING,
    sync_type: str = "bitable",
    feishu_record_id: str | None = None,
    error_message: str | None = None,
    retry_count: int = 0,
) -> FeishuSyncRecord:
    record = FeishuSyncRecord(
        product_id=product.id,
        sync_status=sync_status.value,
        sync_type=sync_type,
        feishu_record_id=feishu_record_id,
        error_message=error_message,
        retry_count=retry_count,
    )
    db_session.add(record)
    await db_session.flush()
    await db_session.refresh(record)
    return record


class TestSyncApiIntegration:
    """End-to-end Sync Record API tests using overridden DB dependency."""

    def test_list_empty(self, override_get_db):
        resp = client.get("/api/v1/sync-records")

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)
        record = await create_sync_record(
            db_session,
            product,
            sync_status=SyncStatus.SUCCESS,
            feishu_record_id="rec_test_1",
        )

        resp = client.get("/api/v1/sync-records")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(record.id)
        assert data["items"][0]["product_id"] == str(product.id)
        assert data["items"][0]["sync_status"] == "success"
        assert data["items"][0]["feishu_record_id"] == "rec_test_1"

    @pytest.mark.asyncio
    async def test_get_detail(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)
        record = await create_sync_record(
            db_session,
            product,
            sync_status=SyncStatus.FAILED,
            error_message="Sync failed",
            retry_count=2,
        )

        resp = client.get(f"/api/v1/sync-records/{record.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(record.id)
        assert data["product_id"] == str(product.id)
        assert data["sync_status"] == "failed"
        assert data["error_message"] == "Sync failed"
        assert data["retry_count"] == 2

    def test_get_not_found(self, override_get_db):
        resp = client.get(f"/api/v1/sync-records/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)
        await create_sync_record(
            db_session,
            product,
            sync_status=SyncStatus.PENDING,
        )
        success_record = await create_sync_record(
            db_session,
            product,
            sync_status=SyncStatus.SUCCESS,
        )

        resp = client.get("/api/v1/sync-records?status=success")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(success_record.id)
        assert data["items"][0]["sync_status"] == "success"

    @pytest.mark.asyncio
    async def test_filter_by_product_id(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(
            db_session,
            unique_key="example.com/filter-product",
        )
        other_product = await create_product(
            db_session,
            unique_key="example.com/other-product",
        )
        record = await create_sync_record(db_session, product)
        await create_sync_record(db_session, other_product)

        resp = client.get(f"/api/v1/sync-records?product_id={product.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(record.id)
        assert data["items"][0]["product_id"] == str(product.id)
