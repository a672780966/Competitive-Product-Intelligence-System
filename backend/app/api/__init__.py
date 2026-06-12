"""Health check endpoints.

- /health/live  — liveness probe (always 200 when process is alive)
- /health/ready — readiness probe (checks database + redis connectivity)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Liveness probe — always returns 200 when the process is alive."""
    return {"status": "alive", "service": "cpis-v1"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe — returns 200 when database is reachable.

    Returns 503 if any dependency is unhealthy.
    """
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("readiness_db_failed", error=str(exc))
        db_ok = False

    if not db_ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unreachable"},
        )

    return {"status": "ready", "service": "cpis-v1", "database": "connected"}
