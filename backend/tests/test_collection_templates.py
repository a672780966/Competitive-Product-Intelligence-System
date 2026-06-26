"""Tests for Node 6 — CollectionTemplate API.

Tests the template endpoints and TemplateService.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.main import app
from app.models import Base, CollectionTemplate
from app.models.enums import CollectionTemplateStatus

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
    """Create a sample template in the database."""
    template = CollectionTemplate(
        name="Test Template",
        description="A test template",
        target_brand="test_brand",
        topic="smartphone",
        source_plan={
            "query": "test query",
            "sources": [
                {"title": "Source 1", "url": "https://example.com/1", "domain": "example.com"},
            ],
        },
        run_plan={
            "version": "1.0",
            "name": "Test Template",
            "sources": [
                {
                    "type": "url_list",
                    "urls": ["https://example.com/1"],
                    "category_hint": "smartphone",
                },
            ],
        },
        status=CollectionTemplateStatus.ACTIVE,
    )
    db_session.add(template)
    await db_session.flush()
    return template


# ══════════════════════════════════════════════════════════════════
# Template Service Tests
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestTemplateService:
    """Tests for TemplateService."""

    async def test_list_templates_empty(self, db_session: AsyncSession):
        """Should return empty list when no templates exist."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.list_templates()
        assert result.total == 0
        assert result.items == []

    async def test_create_and_list_templates(self, db_session: AsyncSession, sample_template):
        """Should list created templates."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.list_templates()
        assert result.total == 1
        assert result.items[0].name == "Test Template"

    async def test_get_template(self, db_session: AsyncSession, sample_template):
        """Should get a template by ID."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.get_template(sample_template.id)
        assert result is not None
        assert result.name == "Test Template"
        assert result.target_brand == "test_brand"

    async def test_get_template_not_found(self, db_session: AsyncSession):
        """Should return None for non-existent template."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.get_template(uuid.uuid4())
        assert result is None

    async def test_update_template_name(self, db_session: AsyncSession, sample_template):
        """Should update template name."""
        from app.schemas.template_schedule import TemplateUpdateRequest
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.update_template(
            sample_template.id,
            TemplateUpdateRequest(name="Updated Name"),
        )
        assert result is not None
        assert result.name == "Updated Name"

    async def test_update_template_status(self, db_session: AsyncSession, sample_template):
        """Should update template status."""
        from app.schemas.template_schedule import TemplateUpdateRequest
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.update_template(
            sample_template.id,
            TemplateUpdateRequest(status=CollectionTemplateStatus.ARCHIVED),
        )
        assert result is not None
        assert result.status == "archived"

    async def test_update_template_not_found(self, db_session: AsyncSession):
        """Should return None when updating non-existent template."""
        from app.schemas.template_schedule import TemplateUpdateRequest
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.update_template(
            uuid.uuid4(),
            TemplateUpdateRequest(name="New Name"),
        )
        assert result is None

    async def test_list_templates_with_search(self, db_session: AsyncSession, sample_template):
        """Should filter templates by search term."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.list_templates(search="Test")
        assert result.total == 1

        result = await service.list_templates(search="NonExistent")
        assert result.total == 0

    async def test_list_templates_with_status_filter(self, db_session: AsyncSession, sample_template):
        """Should filter templates by status."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.list_templates(status=CollectionTemplateStatus.ACTIVE)
        assert result.total == 1

        result = await service.list_templates(status=CollectionTemplateStatus.ARCHIVED)
        assert result.total == 0

    async def test_run_template(self, db_session: AsyncSession, sample_template):
        """Should run a template and create tasks."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)

        with patch(
            "app.services.collection_runner_service.RunPlanExecutor.execute_plan",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = []
            result = await service.run_template(sample_template.id)
            assert result is not None
            assert result.template_id == sample_template.id

    async def test_run_template_not_found(self, db_session: AsyncSession):
        """Should return None when running non-existent template."""
        from app.services.template_service import TemplateService

        service = TemplateService(db_session)
        result = await service.run_template(uuid.uuid4())
        assert result is None


# ══════════════════════════════════════════════════════════════════
# Template API Tests
# ══════════════════════════════════════════════════════════════════


class TestTemplateAPI:
    """Tests for template API endpoints."""

    def test_list_templates_empty(self, override_get_db):
        """GET /api/v1/collection-templates should return empty list."""
        resp = client.get("/api/v1/collection-templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_templates_with_data(self, override_get_db, db_session: AsyncSession, sample_template):
        """GET /api/v1/collection-templates should return templates."""
        resp = client.get("/api/v1/collection-templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_get_template(self, override_get_db, db_session: AsyncSession, sample_template):
        """GET /api/v1/collection-templates/{id} should return template."""
        resp = client.get(f"/api/v1/collection-templates/{sample_template.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Template"

    def test_get_template_not_found(self, override_get_db):
        """GET /api/v1/collection-templates/{id} should 404."""
        resp = client.get(f"/api/v1/collection-templates/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_patch_template(self, override_get_db, db_session: AsyncSession, sample_template):
        """PATCH /api/v1/collection-templates/{id} should update."""
        resp = client.patch(
            f"/api/v1/collection-templates/{sample_template.id}",
            json={"name": "Patched Name", "description": "Updated desc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Patched Name"
        assert data["description"] == "Updated desc"

    def test_patch_template_not_found(self, override_get_db):
        """PATCH /api/v1/collection-templates/{id} should 404."""
        resp = client.patch(
            f"/api/v1/collection-templates/{uuid.uuid4()}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 404

    def test_patch_template_status(self, override_get_db, db_session: AsyncSession, sample_template):
        """PATCH should update template status."""
        resp = client.patch(
            f"/api/v1/collection-templates/{sample_template.id}",
            json={"status": "archived"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"

    def test_run_template(self, override_get_db, db_session: AsyncSession, sample_template):
        """POST /api/v1/collection-templates/{id}/run should execute."""
        from app.services.template_service import TemplateService

        with patch.object(TemplateService, "run_template", new_callable=AsyncMock) as mock_run:
            from app.schemas.template_schedule import TemplateRunResponse

            mock_run.return_value = TemplateRunResponse(
                template_id=sample_template.id,
                tasks_created=3,
                message="Template executed: 3 tasks created",
            )

            resp = client.post(f"/api/v1/collection-templates/{sample_template.id}/run")
            assert resp.status_code == 201
            data = resp.json()
            assert data["tasks_created"] == 3

    def test_run_template_not_found(self, override_get_db):
        """POST run on non-existent template should 404."""
        resp = client.post(f"/api/v1/collection-templates/{uuid.uuid4()}/run")
        assert resp.status_code == 404

    def test_list_templates_pagination(self, override_get_db, db_session: AsyncSession):
        """Should support pagination."""
        # Create multiple templates
        for i in range(5):
            t = CollectionTemplate(
                name=f"Template {i}",
                source_plan={},
                run_plan={"version": "1.0", "sources": [{"type": "url_list", "urls": ["https://example.com"]}]},
                status=CollectionTemplateStatus.ACTIVE,
            )
            db_session.add(t)
        db_session.flush()

        resp = client.get("/api/v1/collection-templates?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_templates_search_filter(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should filter templates by search term."""
        resp = client.get("/api/v1/collection-templates?search=Test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        resp = client.get("/api/v1/collection-templates?search=NonExistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_list_templates_status_filter(self, override_get_db, db_session: AsyncSession, sample_template):
        """Should filter templates by status."""
        resp = client.get("/api/v1/collection-templates?status=active")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        resp = client.get("/api/v1/collection-templates?status=archived")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


# ══════════════════════════════════════════════════════════════════
# Template Response Schema Tests
# ══════════════════════════════════════════════════════════════════


class TestTemplateSchemas:
    """Tests for template Pydantic schemas."""

    def test_template_update_request(self):
        """Should validate update request."""
        from app.schemas.template_schedule import TemplateUpdateRequest

        req = TemplateUpdateRequest(name="Test", description="Desc")
        assert req.name == "Test"
        assert req.description == "Desc"

    def test_template_update_request_empty(self):
        """Should allow all fields to be None."""
        from app.schemas.template_schedule import TemplateUpdateRequest

        req = TemplateUpdateRequest()
        assert req.name is None
        assert req.description is None
        assert req.status is None

    def test_template_run_response(self):
        """Should build run response."""
        from app.schemas.template_schedule import TemplateRunResponse

        resp = TemplateRunResponse(
            template_id=uuid.uuid4(),
            tasks_created=5,
            message="Done",
        )
        assert resp.tasks_created == 5

    def test_template_response_from_attributes(self):
        """TemplateResponse should support from_attributes."""
        from app.schemas.template_schedule import TemplateResponse

        # Verify model_config has from_attributes
        assert TemplateResponse.model_config.get("from_attributes") is True
        assert "id" in TemplateResponse.model_fields
        assert "name" in TemplateResponse.model_fields
        assert "status" in TemplateResponse.model_fields
