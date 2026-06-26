"""Tests for Node 4 — Discovery API endpoints."""

from __future__ import annotations

import uuid

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
# Session API Tests
# ══════════════════════════════════════════════════════════════════


class TestCreateDiscoverySession:
    """POST /api/v1/discovery/sessions"""

    def test_create_session(self, override_get_db):
        resp = client.post(
            "/api/v1/discovery/sessions",
            json={
                "query": "xiaomi 14 ultra",
                "target_brand": "xiaomi",
                "topic": "smartphone",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["query"] == "xiaomi 14 ultra"
        assert data["target_brand"] == "xiaomi"
        assert data["topic"] == "smartphone"
        assert "id" in data
        assert data["status"] == "completed"
        assert data["candidate_count"] > 0

    def test_create_session_minimal(self, override_get_db):
        resp = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "test query"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["query"] == "test query"
        assert data["target_brand"] is None
        assert data["topic"] is None

    def test_create_session_empty_query(self, override_get_db):
        resp = client.post(
            "/api/v1/discovery/sessions",
            json={"query": ""},
        )
        assert resp.status_code == 422  # Validation error

    def test_create_session_missing_query(self, override_get_db):
        resp = client.post(
            "/api/v1/discovery/sessions",
            json={},
        )
        assert resp.status_code == 422  # Validation error


class TestGetDiscoverySession:
    """GET /api/v1/discovery/sessions/{id}"""

    def _create_session(self) -> dict:
        resp = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        )
        return resp.json()

    def test_get_session(self, override_get_db):
        created = self._create_session()
        resp = client.get(f"/api/v1/discovery/sessions/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["id"] == created["id"]
        assert data["session"]["query"] == "xiaomi 14 ultra"
        assert len(data["candidates"]) > 0

    def test_get_session_not_found(self, override_get_db):
        resp = client.get(f"/api/v1/discovery/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_session_invalid_uuid(self, override_get_db):
        resp = client.get("/api/v1/discovery/sessions/not-a-uuid")
        assert resp.status_code == 422

    def test_session_candidates_have_all_fields(self, override_get_db):
        """Candidates in session detail should have risk/collector fields."""
        created = self._create_session()
        resp = client.get(f"/api/v1/discovery/sessions/{created['id']}")
        data = resp.json()
        for c in data["candidates"]:
            assert "id" in c
            assert "url" in c
            assert "domain" in c
            assert "source_type" in c
            assert "risk_level" in c
            assert "recommended_collector" in c
            assert "selected" in c


class TestListDiscoverySessions:
    """GET /api/v1/discovery/sessions"""

    def test_list_sessions(self, override_get_db):
        # Create a couple sessions
        client.post("/api/v1/discovery/sessions", json={"query": "test1"})
        client.post("/api/v1/discovery/sessions", json={"query": "test2"})

        resp = client.get("/api/v1/discovery/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_list_sessions_pagination(self, override_get_db):
        resp = client.get("/api/v1/discovery/sessions?page=1&page_size=5")
        assert resp.status_code == 200
        assert "items" in resp.json()
        assert "total_pages" in resp.json()


class TestListSessionCandidates:
    """GET /api/v1/discovery/sessions/{id}/candidates"""

    def test_list_candidates(self, override_get_db):
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()

        resp = client.get(
            f"/api/v1/discovery/sessions/{created['id']}/candidates",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert len(data["items"]) > 0

    def test_list_candidates_not_found(self, override_get_db):
        resp = client.get(
            f"/api/v1/discovery/sessions/{uuid.uuid4()}/candidates",
        )
        assert resp.status_code == 404

    def test_list_candidates_pagination(self, override_get_db):
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()

        resp = client.get(
            f"/api/v1/discovery/sessions/{created['id']}/candidates?page=1&page_size=3",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 3


# ══════════════════════════════════════════════════════════════════
# Candidate Update Tests
# ══════════════════════════════════════════════════════════════════


class TestUpdateCandidate:
    """PATCH /api/v1/discovery/candidates/{id}"""

    def _create_session_with_candidate(self) -> tuple[dict, str]:
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()
        session_resp = client.get(
            f"/api/v1/discovery/sessions/{created['id']}",
        ).json()
        candidate_id = session_resp["candidates"][0]["id"]
        return created, candidate_id

    def test_update_candidate_select(self, override_get_db):
        _, candidate_id = self._create_session_with_candidate()

        resp = client.patch(
            f"/api/v1/discovery/candidates/{candidate_id}",
            json={"selected": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected"] is True
        assert data["id"] == candidate_id

    def test_update_candidate_deselect(self, override_get_db):
        _, candidate_id = self._create_session_with_candidate()

        client.patch(
            f"/api/v1/discovery/candidates/{candidate_id}",
            json={"selected": True},
        )
        resp = client.patch(
            f"/api/v1/discovery/candidates/{candidate_id}",
            json={"selected": False},
        )
        assert resp.status_code == 200
        assert resp.json()["selected"] is False

    def test_update_candidate_not_found(self, override_get_db):
        resp = client.patch(
            f"/api/v1/discovery/candidates/{uuid.uuid4()}",
            json={"selected": True},
        )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Batch Select Tests
# ══════════════════════════════════════════════════════════════════


class TestBatchSelect:
    """POST /api/v1/discovery/sessions/{id}/select"""

    def _create_session_with_candidates(self) -> tuple[str, list[str]]:
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()
        session_resp = client.get(
            f"/api/v1/discovery/sessions/{created['id']}",
        ).json()
        candidate_ids = [c["id"] for c in session_resp["candidates"][:3]]
        return created["id"], candidate_ids

    def test_batch_select(self, override_get_db):
        session_id, candidate_ids = self._create_session_with_candidates()

        resp = client.post(
            f"/api/v1/discovery/sessions/{session_id}/select",
            json={
                "candidate_ids": candidate_ids,
                "selected": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == len(candidate_ids)
        assert data["selected"] is True

    def test_batch_deselect(self, override_get_db):
        session_id, candidate_ids = self._create_session_with_candidates()

        # First select
        client.post(
            f"/api/v1/discovery/sessions/{session_id}/select",
            json={"candidate_ids": candidate_ids, "selected": True},
        )
        # Then deselect
        resp = client.post(
            f"/api/v1/discovery/sessions/{session_id}/select",
            json={"candidate_ids": candidate_ids, "selected": False},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == len(candidate_ids)
        assert resp.json()["selected"] is False

    def test_batch_select_invalid_session(self, override_get_db):
        resp = client.post(
            f"/api/v1/discovery/sessions/{str(uuid.uuid4())}/select",
            json={"candidate_ids": [str(uuid.uuid4())], "selected": True},
        )
        # Session doesn't exist but we still attempt the operation
        # Repository batch_update does not validate session
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════
# Create Template from Selection Tests
# ══════════════════════════════════════════════════════════════════


class TestCreateTemplateFromSelection:
    """POST /api/v1/discovery/sessions/{id}/create-template"""

    def _setup_session_with_selection(self) -> str:
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()
        session_resp = client.get(
            f"/api/v1/discovery/sessions/{created['id']}",
        ).json()
        candidate_ids = [c["id"] for c in session_resp["candidates"][:3]]
        client.post(
            f"/api/v1/discovery/sessions/{created['id']}/select",
            json={"candidate_ids": candidate_ids, "selected": True},
        )
        return created["id"]

    def test_create_template(self, override_get_db):
        session_id = self._setup_session_with_selection()

        resp = client.post(
            f"/api/v1/discovery/sessions/{session_id}/create-template",
            json={
                "name": "Xiaomi 14 Ultra Sources",
                "description": "Track Xiaomi 14 Ultra info",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Xiaomi 14 Ultra Sources"
        assert data["candidate_count"] == 3
        assert "template_id" in data

    def test_create_template_no_selection(self, override_get_db):
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()

        resp = client.post(
            f"/api/v1/discovery/sessions/{created['id']}/create-template",
            json={"name": "Empty Template"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["candidate_count"] == 0

    def test_create_template_session_not_found(self, override_get_db):
        resp = client.post(
            f"/api/v1/discovery/sessions/{uuid.uuid4()}/create-template",
            json={"name": "Ghost Template"},
        )
        assert resp.status_code == 404

    def test_create_template_missing_name(self, override_get_db):
        created = client.post(
            "/api/v1/discovery/sessions",
            json={"query": "xiaomi 14 ultra"},
        ).json()

        resp = client.post(
            f"/api/v1/discovery/sessions/{created['id']}/create-template",
            json={},
        )
        assert resp.status_code == 422  # Validation error
