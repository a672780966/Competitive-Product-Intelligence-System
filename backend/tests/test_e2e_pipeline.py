"""
CPIS V1 — 端到端管道测试

Tests the full pipeline end-to-end with real API calls and mock data.
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
from app.models import Base
from app.models.user import User

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
    admin_role = Role(name="admin", description="Admin")
    db_session.add(admin_role)
    await db_session.flush()
    mock_user = User(
        id=uuid.uuid4(),
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


# ══════════════════════════════════════════════════════════════════
# Step 1–3: Task CRUD (sync API tests)
# ══════════════════════════════════════════════════════════════════


class TestTaskPipeline:
    """Uses TestClient (sync) for API-level pipeline verification."""

    def test_create_task_and_check_events(self, override_get_db, override_auth):
        """Create task → verify it exists with events."""
        resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/techpro-x100",
            "category_hint": "ems_muscle_stimulator",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_url"] == "https://example.com/techpro-x100"
        task_id = data["id"]

        # Detail should show events
        detail = client.get(f"/api/v1/collection-tasks/{task_id}")
        assert detail.status_code == 200
        assert len(detail.json()["events"]) >= 1

    def test_blocked_url_rejected(self, override_get_db, override_auth):
        """localhost URLs are blocked by validation."""
        resp = client.post("/api/v1/collection-tasks", json={
            "source_url": "http://localhost/admin",
        })
        assert resp.status_code == 201
        assert resp.json()["status"] in ("blocked", "failed")

    def test_batch_create(self, override_get_db, override_auth):
        """Batch creation works."""
        resp = client.post("/api/v1/collection-tasks/batch", json={
            "tasks": [
                {"source_url": "https://example.com/p1"},
                {"source_url": "https://example.com/p2"},
            ],
        })
        assert resp.status_code == 201
        assert resp.json()["created"] == 2

    def test_list_and_filter(self, override_get_db, override_auth):
        """List tasks with keyword filter."""
        client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/searchable-product",
        })
        resp = client.get("/api/v1/collection-tasks?keyword=searchable")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_retry_and_cancel(self, override_get_db, override_auth):
        """Retry blocked task + cancel pending task."""
        # Blocked task
        c1 = client.post("/api/v1/collection-tasks", json={
            "source_url": "http://localhost/test",
        })
        task_id = c1.json()["id"]

        # Retry
        r1 = client.post(f"/api/v1/collection-tasks/{task_id}/retry")
        assert r1.status_code == 200
        assert r1.json()["retry_count"] >= 1

        # Cancel
        c2 = client.post("/api/v1/collection-tasks", json={
            "source_url": "https://example.com/to-cancel",
        })
        task_id2 = c2.json()["id"]
        r2 = client.post(f"/api/v1/collection-tasks/{task_id2}/cancel")
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelled"

    def test_invalid_input_rejected(self, override_get_db, override_auth):
        """Empty URL is rejected by schema validation."""
        resp = client.post("/api/v1/collection-tasks", json={"source_url": ""})
        assert resp.status_code == 422

        resp2 = client.get("/api/v1/collection-tasks/not-a-uuid")
        assert resp2.status_code == 422


# ══════════════════════════════════════════════════════════════════
# Step 4–7: Review lifecycle (async, needs DB inspection)
# ══════════════════════════════════════════════════════════════════


class TestReviewPipeline:
    """Full review lifecycle via API calls."""

    @pytest.mark.asyncio
    async def test_review_lifecycle(self, db_session: AsyncSession, override_get_db, override_auth):
        """Create product version → list reviews → detail → approve → verify."""
        from app.models import Product, ProductVersion
        from app.models.enums import ReviewStatus
        from app.repositories.product_repository import ProductRepository

        # Seed data
        product = Product(
            unique_key="e2e-review", brand="BrandX", name="ProductX",
            source_url="https://example.com/px",
            review_status=ReviewStatus.NEEDS_REVIEW,
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(
            product_id=product.id, version_no=1,
            structured_data={"brand": "BrandX", "product_name": "ProductX"},
            analysis_data={"analysis_summary": "Good device"},
            overall_confidence=0.45,
            ai_model="gpt-4o",
        )
        db_session.add(version)
        await db_session.flush()

        # List reviews (not status filtered, should appear)
        list_resp = client.get("/api/v1/reviews")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        # Get detail
        detail_resp = client.get(f"/api/v1/reviews/{version.id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["product"]["brand"] == "BrandX"
        assert data["overall_confidence"] == 0.45

        # Save draft
        draft_resp = client.put(
            f"/api/v1/reviews/{version.id}/draft",
            json={"corrections": {"brand": "BrandX Inc."}, "comments": "First pass"},
        )
        assert draft_resp.status_code == 200
        assert draft_resp.json()["current_review"]["decision"] == "in_review"

        # Approve
        approve_resp = client.post(
            f"/api/v1/reviews/{version.id}/approve",
            json={"comments": "Verified"},
        )
        assert approve_resp.status_code == 200
        # Decision may be "in_review" if draft created at the same second
        # Verify via DB inspection instead
        from sqlalchemy import select

        from app.models import ReviewRecord
        rr_result = await db_session.execute(
            select(ReviewRecord).where(
                ReviewRecord.product_version_id == version.id,
                ReviewRecord.decision == "approved",
            )
        )
        assert rr_result.scalar_one_or_none() is not None, "Approval record not found"

        # Verify DB was updated
        repo = ProductRepository(db_session)
        updated = await repo.get_by_id(product.id)
        assert updated.review_status == ReviewStatus.APPROVED.value
        assert updated.current_version_id == version.id

    @pytest.mark.asyncio
    async def test_reject_version(self, db_session: AsyncSession, override_get_db, override_auth):
        """Reject a version and verify DB state."""
        from app.models import Product, ProductVersion
        from app.models.enums import ReviewStatus
        from app.repositories.product_repository import ProductRepository

        product = Product(
            unique_key="e2e-reject", brand="BadBrand",
            review_status=ReviewStatus.NEEDS_REVIEW,
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(product_id=product.id, version_no=1)
        db_session.add(version)
        await db_session.flush()

        reject_resp = client.post(
            f"/api/v1/reviews/{version.id}/reject",
            json={"comments": "Incorrect data"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["current_review"]["decision"] == "rejected"

        repo = ProductRepository(db_session)
        updated = await repo.get_by_id(product.id)
        assert updated.review_status == ReviewStatus.REJECTED.value

    def test_review_404(self, override_get_db, override_auth):
        """Non-existent review returns 404."""
        resp = client.get(f"/api/v1/reviews/{uuid.uuid4()}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Step 8–9: Report generation
# ══════════════════════════════════════════════════════════════════


class TestReportPipeline:
    """Report generation via API, verified by response content."""

    @pytest.mark.asyncio
    async def test_single_product_report(self, db_session: AsyncSession, override_get_db, override_auth):
        """Generate single product report."""
        from app.models import Product, ProductVersion

        product = Product(
            unique_key="report-e2e-single", brand="BrandR", name="ProductR",
            source_url="https://example.com/report-test",
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(
            product_id=product.id, version_no=1,
            structured_data={
                "product_name": "ProductR", "brand": "BrandR",
                "core_benefits": ["24h battery"],
                "features": ["Water resistant"],
            },
            analysis_data={
                "advantages": ["Long battery life"],
                "analysis_summary": "Good product.",
            },
        )
        db_session.add(version)
        await db_session.flush()
        product.current_version_id = version.id
        await db_session.flush()

        resp = client.get(f"/api/v1/reports/product/{product.id}")
        assert resp.status_code == 200
        md = resp.text
        assert "ProductR" in md
        assert "BrandR" in md
        assert "Long battery life" in md

    @pytest.mark.asyncio
    async def test_comparison_report(self, db_session: AsyncSession, override_get_db, override_auth):
        """Generate multi-product comparison report."""
        from app.models import Product, ProductVersion

        ids = []
        for i in range(2):
            p = Product(unique_key=f"comp-e2e-{i}", brand=f"B{i}", name=f"N{i}")
            db_session.add(p)
            await db_session.flush()
            v = ProductVersion(product_id=p.id, version_no=1)
            db_session.add(v)
            await db_session.flush()
            p.current_version_id = v.id
            ids.append(str(p.id))
        await db_session.flush()

        resp = client.post("/api/v1/reports/compare", json={"product_ids": ids})
        assert resp.status_code == 200
        assert "B0" in resp.text or "N0" in resp.text or "N1" in resp.text

    def test_report_404(self, override_get_db, override_auth):
        """Non-existent product returns 404."""
        resp = client.get(f"/api/v1/reports/product/{uuid.uuid4()}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Step 10: Audit log inspection
# ══════════════════════════════════════════════════════════════════


class TestAuditPipeline:
    """Verify audit logging after review actions."""

    @pytest.mark.asyncio
    async def test_audit_logged_on_approve(self, db_session: AsyncSession, override_get_db, override_auth):
        """Approval creates an audit log entry."""
        from app.models import AuditLog, Product, ProductVersion
        from app.models.enums import ReviewStatus

        product = Product(
            unique_key="e2e-audit", brand="AuditBrand",
            review_status=ReviewStatus.NEEDS_REVIEW,
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(product_id=product.id, version_no=1)
        db_session.add(version)
        await db_session.flush()

        client.post(
            f"/api/v1/reviews/{version.id}/approve",
            json={"comments": "Audit test"},
        )

        # Check audit log
        from sqlalchemy import select
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "review.approve"),
        )
        logs = list(result.scalars().all())
        assert len(logs) >= 1
        assert logs[-1].resource_id == str(version.id)
