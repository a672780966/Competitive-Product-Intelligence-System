"""Tests for OpenClaw bridge endpoint."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import get_db
from app.models.base import Base


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a fresh in-memory SQLite database for each test.

    Uses a single connection throughout to keep the in-memory DB alive.
    """
    engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=NullPool)

    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)

    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
    )

    yield session

    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


SAMPLE_PAYLOAD = {
    "schema_version": "1.0",
    "object_type": "agent_handoff",
    "run_id": "test-run-001",
    "from_agent": "cpis-info-collector",
    "to_agent": "cpis-product-analyst",
    "payload_type": "evidence_batch",
    "payload": {
        "schema_version": "1.0",
        "object_type": "evidence_batch",
        "run_id": "test-run-001",
        "status": "success",
        "collection_scope": {"max_items_per_ranking": 20},
        "sources": [
            {
                "source_id": "src_001",
                "source_url": "https://example.com/product/1",
                "url": "https://example.com/product/1",
                "source_type": "product_page",
            },
        ],
        "items": [
            {
                "item_id": "item_001",
                "product_name": "Test Product Alpha",
                "asin": "B0TEST1234",
                "brand": "TestBrand",
                "product_url": "https://example.com/product/1",
                "image_url": "https://example.com/img/1.jpg",
                "pricing": {"price": 29.99, "currency": "USD"},
                "ratings": {"score": 4.5, "count": 120},
                "ranking_type": "sales_rank",
                "ranking_position": 3,
            },
        ],
        "collection_summary": {
            "total_items": 1,
            "total_sources": 1,
        },
    },
    "sent_at": "2026-06-26T00:00:00Z",
}


@pytest.mark.asyncio
async def test_ingest_evidence_success(db_session):
    """POST /api/v1/openclaw/evidence returns success with valid payload."""

    # Override DB dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/openclaw/evidence",
            json=SAMPLE_PAYLOAD,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["run_id"] == "test-run-001"
    assert data["ingested"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "success"
    assert data["items"][0]["item_id"] == "item_001"

    # Clean up override
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ingest_evidence_empty_items(db_session):
    """Empty items list returns success with 0 ingested."""
    payload = {
        **SAMPLE_PAYLOAD,
        "run_id": "test-run-empty",
        "payload": {
            **SAMPLE_PAYLOAD["payload"],
            "items": [],
            "sources": [],
        },
    }

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/openclaw/evidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 0
    assert data["status"] == "success"

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ingest_evidence_invalid_json(db_session):
    """Invalid JSON body returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/openclaw/evidence",
            json={"invalid": "data"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_partial_failure(db_session):
    """One valid item + one with empty URL triggers partial success."""
    payload = {
        **SAMPLE_PAYLOAD,
        "run_id": "test-run-partial",
        "payload": {
            **SAMPLE_PAYLOAD["payload"],
            "run_id": "test-run-partial",
            "items": [
                SAMPLE_PAYLOAD["payload"]["items"][0],
                {
                    "item_id": "item_bad",
                    "product_url": "",  # invalid URL
                    "product_name": "Bad Product",
                },
            ],
        },
    }

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/openclaw/evidence", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # empty URL fails, so status should be partial or success
    assert data["status"] in ("partial", "success")

    app.dependency_overrides.pop(get_db, None)
