"""
FastAPI application entry point.

Defines the app factory with async lifespan management:
settings -> logging -> registry -> event subscriptions -> ready.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app_name.config import Settings

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown logic."""
    from app_name.config import get_settings
    from app_name.core.logging import setup_logging
    from app_name.core.service_factory import build_registry

    # 1. Load settings
    settings = get_settings()

    # 2. Configure logging
    setup_logging(settings.logging)
    logger.info("Starting app_name v{}", __version__)

    # 3. Build the application registry (services, event bus, factories)
    registry = build_registry(settings=settings)
    app.state.registry = registry

    # 4. Subscribe domain event handlers
    # Example: registry.event_bus.subscribe(SomeEvent, some_handler)
    logger.info("Application startup complete")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    logger.info("Shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI application instance."""
    if settings is None:
        from app_name.config import get_settings

        settings = get_settings()

    app = FastAPI(
        title="app_name",
        version=__version__,
        lifespan=lifespan,
    )

    # --- Exception handlers ---
    from app_name.shared.exceptions.handlers import register_exception_handlers

    register_exception_handlers(app)

    # --- Middleware (outermost first) ---
    from app_name.shared.middleware.request_context import RequestContextMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    app.add_middleware(RequestContextMiddleware)

    # --- Routers ---
    from app_name.api.v1.router import router as v1_router

    app.include_router(v1_router)

    # --- Health check ---
    from app_name.shared.schemas.response import APIResponse

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return APIResponse.ok(data={"status": "ok", "version": __version__}).model_dump()

    return app
