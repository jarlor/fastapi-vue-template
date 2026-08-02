"""Versioned public API composition."""

from __future__ import annotations

from fastapi import APIRouter

from app.contexts.tasks.interface.api.router import router as tasks_router
from app.metadata import __version__
from app.shared.schemas.response import APIResponse, HealthStatus

router = APIRouter(prefix="/api/v1")


@router.get("/health", tags=["health"], response_model=APIResponse[HealthStatus])
async def health() -> APIResponse[HealthStatus]:
    return APIResponse.ok(data=HealthStatus(status="ok", version=__version__))


router.include_router(tasks_router)
