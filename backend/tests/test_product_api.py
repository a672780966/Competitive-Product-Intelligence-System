"""
CPIS V1 - Product API integration tests.

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
from app.models import Base, Product, ProductVersion
from app.models.enums import ReviewStatus

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
    brand: str | None = "TestBrand",
    name: str | None = "Test Product",
    model: str | None = "TM-100",
    review_status: ReviewStatus = ReviewStatus.PENDING,
) -> Product:
    product = Product(
        unique_key=unique_key,
        brand=brand,
        name=name,
        model=model,
        category="smartphone",
        review_status=review_status,
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product


async def create_version(
    db_session: AsyncSession,
    product: Product,
    *,
    version_no: int = 1,
) -> ProductVersion:
    version = ProductVersion(
        product_id=product.id,
        version_no=version_no,
        overall_confidence=0.91,
        ai_model="gpt-4o",
        prompt_version="v1.0",
    )
    db_session.add(version)
    await db_session.flush()
    await db_session.refresh(version)
    product.current_version_id = version.id
    await db_session.flush()
    await db_session.refresh(product)
    return version


class TestProductApiIntegration:
    """End-to-end Product API tests using overridden DB dependency."""

    def test_list_products_empty(self, override_get_db):
        resp = client.get("/api/v1/products")

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_products_with_data(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)

        resp = client.get("/api/v1/products")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(product.id)
        assert data["items"][0]["brand"] == "TestBrand"

    @pytest.mark.asyncio
    async def test_get_product_detail(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)
        version = await create_version(db_session, product)

        resp = client.get(f"/api/v1/products/{product.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(product.id)
        assert data["current_version_id"] == str(version.id)
        assert len(data["versions"]) == 1
        assert data["versions"][0]["id"] == str(version.id)
        assert data["versions"][0]["version_no"] == 1

    @pytest.mark.asyncio
    async def test_get_product_versions(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(db_session)
        version = await create_version(db_session, product)

        resp = client.get(f"/api/v1/products/{product.id}/versions")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(version.id)
        assert data[0]["overall_confidence"] == 0.91

    def test_get_product_not_found(self, override_get_db):
        resp = client.get(f"/api/v1/products/{uuid.uuid4()}")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        await create_product(
            db_session,
            unique_key="example.com/pending-product",
            review_status=ReviewStatus.PENDING,
        )
        await create_product(
            db_session,
            unique_key="example.com/approved-product",
            review_status=ReviewStatus.APPROVED,
        )

        resp = client.get("/api/v1/products?status=approved")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["unique_key"] == "example.com/approved-product"
        assert data["items"][0]["review_status"] == "approved"

    @pytest.mark.asyncio
    async def test_filter_by_keyword(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        product = await create_product(
            db_session,
            unique_key="example.com/search-product",
            brand="Acme",
            name="Searchable Phone",
            model="SP-200",
        )

        resp = client.get("/api/v1/products?keyword=searchable")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(product.id)

    @pytest.mark.asyncio
    async def test_filter_by_domain(
        self,
        override_get_db,
        db_session: AsyncSession,
    ):
        from app.models import Product
        from app.models.enums import ReviewStatus

        # Product in example.com domain
        await create_product(
            db_session,
            unique_key="example.com/domain-test",
            brand="DomainBrand",
        )
        # Product in other domain
        other = Product(
            unique_key="othersite.com/domain-test",
            brand="OtherBrand",
            category="smartphone",
            review_status=ReviewStatus.PENDING,
        )
        db_session.add(other)
        await db_session.flush()

        resp = client.get("/api/v1/products?domain=example.com")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["unique_key"] == "example.com/domain-test"
        assert data["items"][0]["brand"] == "DomainBrand"
