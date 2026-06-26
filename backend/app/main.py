"""FastAPI application factory for CPIS V1."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as health_router
from app.api.products import router as products_router
from app.api.reports import router as reports_router
from app.api.reviews import router as reviews_router
from app.api.openclaw import router as openclaw_router
from app.api.sync import router as sync_router
from app.api.tasks import router as tasks_router
from app.api.discovery import router as discovery_router
from app.api.collection_templates import router as collection_templates_router
from app.api.scheduled_collections import router as scheduled_collections_router
from app.api.usage import router as usage_router
from app.api.provider_status import router as provider_status_router
from app.core import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware


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
    # Request-logging middleware (adds request_id to every request)
    app.add_middleware(RequestLoggingMiddleware)

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    app.include_router(health_router, prefix="/health")
    app.include_router(tasks_router)
    app.include_router(reviews_router)
    app.include_router(reports_router)
    app.include_router(products_router)
    app.include_router(openclaw_router)
    app.include_router(sync_router)
    app.include_router(discovery_router)
    app.include_router(collection_templates_router)
    app.include_router(scheduled_collections_router)
    app.include_router(usage_router)
    app.include_router(provider_status_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": f"{settings.APP_NAME} is running."}

    return app


app = create_app()
