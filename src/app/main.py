"""FastAPI composition root and application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.bootstrap import build_container
from app.config import Settings
from app.container import AppContainer
from app.metadata import __version__


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own process-level resources without performing work at import time."""
    from app.core.logging import setup_logging

    setup_logging(app.state.settings.logging)
    logger.info("Starting {} v{}", app.state.settings.app_name, __version__)
    yield
    logger.info("Application shutdown complete")


def create_app(
    settings: Settings | None = None,
    container: AppContainer | None = None,
) -> FastAPI:
    """Build the application with explicitly replaceable dependencies."""
    if settings is None:
        from app.config import get_settings

        settings = get_settings()

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.container = container or build_container()

    from app.shared.exceptions.handlers import register_exception_handlers
    from app.shared.middleware.request_context import RequestContextMiddleware

    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    app.add_middleware(RequestContextMiddleware)

    from app.api.v1.router import router as v1_router
    from app.shared.schemas.response import APIResponse, HealthStatus

    app.include_router(v1_router)

    @app.get("/health", tags=["health"], response_model=APIResponse[HealthStatus])
    async def health() -> APIResponse[HealthStatus]:
        return APIResponse.ok(data=HealthStatus(status="ok", version=__version__))

    return app
