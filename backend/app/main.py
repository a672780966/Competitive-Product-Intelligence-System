"""FastAPI application factory for CPIS V1."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as health_router
from app.core import get_settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """Create and return the FastAPI application instance."""
    settings = get_settings()

    # Setup structured logging
    setup_logging(debug=settings.DEBUG)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan: startup / shutdown hooks."""
        # Startup: nothing heavy yet
        yield
        # Shutdown: cleanup

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    app.include_router(health_router, prefix="/health")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": f"{settings.APP_NAME} is running."}

    return app


app = create_app()
