"""
FastAPI application entry point.

Defines the app factory with async lifespan management:
settings -> logging -> MongoDB -> registry -> event subscriptions -> ready.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown logic."""
    from app_name.config import get_settings
    from app_name.core.logging import setup_logging
    from app_name.core.service_factory import build_registry
    from app_name.database.mongo import init_mongo

    # 1. Load settings
    settings = get_settings()

    # 2. Configure logging
    setup_logging(settings.logging.log_dir)
    logger.info("Starting app_name v{}", __version__)

    # 3. Connect to MongoDB with retry
    db = await init_mongo(settings)

    # 4. Build the application registry (services, event bus, factories)
    registry = await build_registry(db=db, settings=settings)
    app.state.registry = registry

    # 5. Subscribe domain event handlers
    # Example: registry.event_bus.subscribe(SomeEvent, some_handler)
    logger.info("Application startup complete")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    await registry.db.disconnect()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Build and return the FastAPI application instance."""
    app = FastAPI(
        title="app_name",
        version=__version__,
        lifespan=lifespan,
    )

    # --- CORS middleware (configured from settings at import time) ---
    from app_name.config import get_settings

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    # --- Routers ---
    from app_name.api.public_v1.router import router as public_v1_router
    from app_name.api.internal_v1.router import router as internal_v1_router

    app.include_router(public_v1_router)
    app.include_router(internal_v1_router)

    # --- Health check ---
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
