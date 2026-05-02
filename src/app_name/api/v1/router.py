"""
API v1 router.

Endpoints here are the default application API surface for the template.
"""

from __future__ import annotations

from fastapi import APIRouter

from app_name.main import __version__
from app_name.shared.schemas.response import APIResponse, HealthStatus

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/health", response_model=APIResponse[HealthStatus])
async def health() -> APIResponse[HealthStatus]:
    """Versioned health check endpoint."""
    return APIResponse.ok(data=HealthStatus(status="ok", version=__version__))


# Include context-specific routers here:
# from app_name.contexts.some_context.interface.api.router import router as some_router
# router.include_router(some_router)
