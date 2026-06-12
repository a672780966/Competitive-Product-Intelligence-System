"""Basic connectivity test for CPIS V1."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live() -> None:
    """GET /health/live should return 200 with status 'alive'."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "cpis-v1"


def test_health_ready() -> None:
    """GET /health/ready should return 200 with status 'ready'."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_root() -> None:
    """GET / should return 200."""
    response = client.get("/")
    assert response.status_code == 200
