"""FastAPI application factory for CPIS V1."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as health_router
from app.api.reports import router as reports_router
from app.api.reviews import router as reviews_router
from app.api.tasks import router as tasks_router
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

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": f"{settings.APP_NAME} is running."}

    return app


app = create_app()
