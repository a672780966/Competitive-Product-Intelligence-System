"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Liveness probe — always returns 200 when the process is alive."""
    return {"status": "alive", "service": "cpis-v1"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe — returns 200 when dependencies are reachable.

    Currently a basic placeholder; will check database & redis connectivity.
    """
    return {"status": "ready", "service": "cpis-v1"}
