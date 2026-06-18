"""
CPIS V1 — 人工复核 API & Service 测试
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models import Base, Product, ProductVersion
from app.models.enums import ReviewStatus
from app.models.user import User
from app.repositories.product_repository import ProductRepository
from app.schemas.review import PaginatedReviewResponse, ReviewListQuery

client = TestClient(app)


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


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def override_auth(db_session: AsyncSession):
    """Override auth to bypass JWT verification during tests."""
    from app.models.user import Role, UserRole as URMdl
    import uuid as _uid
    # Ensure admin role exists
    admin_role = Role(name="admin", description="Admin")
    db_session.add(admin_role)
    await db_session.flush()

    mock_user = User(
        id=_uid.uuid4(),
        username="test_admin",
        password_hash="$2b$12$dummyhashdummyhashdummyhashdummyhashdummyhashdummyhashdummy",
        is_active=True,
    )
    db_session.add(mock_user)
    await db_session.flush()

    db_session.add(URMdl(user_id=mock_user.id, role_id=admin_role.id))
    await db_session.flush()
    await db_session.refresh(mock_user, ["roles"])

    async def _override():
        return mock_user
    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def seeded_db(db_session: AsyncSession) -> tuple[Product, ProductVersion]:
    """Create a product + version for testing."""
    repo = ProductRepository(db_session)
    product = Product(
        unique_key="example.com/test-brand/test-model",
        brand="TestBrand",
        name="Test Product",
        model="TM-100",
        review_status=ReviewStatus.NEEDS_REVIEW,
    )
    product = await repo.create(product)

    version = ProductVersion(
        product_id=product.id,
        version_no=1,
        structured_data={"brand": "TestBrand", "product_name": "Test Product"},
        analysis_data={"analysis_summary": "Test"},
        overall_confidence=0.45,
        ai_model="gpt-4o",
        prompt_version="v1.0",
    )
    version = await repo.create_version(version)
    return product, version


# ══════════════════════════════════════════════════════════════════
# Schema validation
# ══════════════════════════════════════════════════════════════════


class TestReviewSchemas:
    def test_paginated_response(self):
        r = PaginatedReviewResponse(
            items=[], total=0, page=1, page_size=20, total_pages=1,
        )
        assert r.total == 0

    def test_list_query(self):
        q = ReviewListQuery(status=ReviewStatus.NEEDS_REVIEW, page=2, page_size=10)
        assert q.status == ReviewStatus.NEEDS_REVIEW
        assert q.page == 2


# ══════════════════════════════════════════════════════════════════
# Service tests
# ══════════════════════════════════════════════════════════════════


class TestReviewService:
    @pytest.mark.asyncio
    async def test_list_reviews_empty(self, db_session: AsyncSession):
        from app.services.review_service import ReviewService
        service = ReviewService(db_session)
        result = await service.list_reviews(ReviewListQuery())
        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_list_reviews_with_data(self, db_session: AsyncSession, seeded_db):
        from app.services.review_service import ReviewService
        service = ReviewService(db_session)
        result = await service.list_reviews(ReviewListQuery())
        assert result.total >= 1
        item = result.items[0]
        assert item.product.brand == "TestBrand"
        assert item.overall_confidence == 0.45

    @pytest.mark.asyncio
    async def test_get_review_detail(self, db_session: AsyncSession, seeded_db):
        from app.services.review_service import ReviewService
        product, version = seeded_db
        service = ReviewService(db_session)
        detail = await service.get_review_detail(version.id)
        assert detail is not None
        assert detail.product.unique_key == product.unique_key
        assert detail.structured_data["brand"] == "TestBrand"
        assert detail.overall_confidence == 0.45

    @pytest.mark.asyncio
    async def test_save_draft(self, db_session: AsyncSession, seeded_db):
        from app.schemas.review import SaveDraftRequest
        from app.services.review_service import ReviewService
        product, version = seeded_db
        service = ReviewService(db_session)
        detail = await service.save_draft(
            version.id,
            SaveDraftRequest(corrections={"brand": "CorrectedBrand"}, comments="Checked"),
            reviewer="tester",
        )
        assert detail is not None
        assert detail.current_review is not None
        assert detail.current_review["decision"] == ReviewStatus.IN_REVIEW.value

    @pytest.mark.asyncio
    async def test_approve_version(self, db_session: AsyncSession, seeded_db):
        from app.schemas.review import ApproveRequest
        from app.services.review_service import ReviewService
        product, version = seeded_db
        service = ReviewService(db_session)
        detail = await service.approve(
            version.id,
            ApproveRequest(comments="Looks good"),
            reviewer="admin",
        )
        assert detail is not None
        assert detail.current_review["decision"] == ReviewStatus.APPROVED.value

        # Product status should be updated
        repo = ProductRepository(db_session)
        updated = await repo.get_by_id(product.id)
        assert updated.review_status == ReviewStatus.APPROVED.value
        assert updated.current_version_id == version.id

    @pytest.mark.asyncio
    async def test_reject_version(self, db_session: AsyncSession, seeded_db):
        from app.schemas.review import RejectRequest
        from app.services.review_service import ReviewService
        product, version = seeded_db
        service = ReviewService(db_session)
        detail = await service.reject(
            version.id,
            RejectRequest(comments="Incorrect data"),
            reviewer="admin",
        )
        assert detail is not None
        assert detail.current_review["decision"] == ReviewStatus.REJECTED.value

        repo = ProductRepository(db_session)
        updated = await repo.get_by_id(product.id)
        assert updated.review_status == ReviewStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, db_session: AsyncSession):
        from app.services.review_service import ReviewService
        service = ReviewService(db_session)
        result = await service.get_review_detail(uuid.uuid4())
        assert result is None


# ══════════════════════════════════════════════════════════════════
# API integration tests
# ══════════════════════════════════════════════════════════════════


class TestReviewApi:
    def test_list_reviews(self, override_get_db, override_auth, seeded_db):
        resp = client.get("/api/v1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_get_detail_found(self, override_get_db, override_auth, seeded_db):
        product, version = seeded_db
        resp = client.get(f"/api/v1/reviews/{version.id}")
        assert resp.status_code == 200
        assert resp.json()["product"]["brand"] == "TestBrand"

    def test_get_detail_not_found(self, override_get_db, override_auth):
        resp = client.get(f"/api/v1/reviews/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_save_draft(self, override_get_db, override_auth, seeded_db):
        product, version = seeded_db
        resp = client.put(
            f"/api/v1/reviews/{version.id}/draft",
            json={"corrections": {"brand": "NewBrand"}, "comments": "Draft"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_review"]["decision"] == "in_review"

    def test_approve(self, override_get_db, override_auth, seeded_db):
        product, version = seeded_db
        resp = client.post(
            f"/api/v1/reviews/{version.id}/approve",
            json={"comments": "Approved!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_review"]["decision"] == "approved"
        assert data["overall_confidence"] == 0.45

    def test_reject(self, override_get_db, override_auth, seeded_db):
        product, version = seeded_db
        resp = client.post(
            f"/api/v1/reviews/{version.id}/reject",
            json={"comments": "Rejected"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_review"]["decision"] == "rejected"
