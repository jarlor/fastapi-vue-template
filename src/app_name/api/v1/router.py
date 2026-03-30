"""
API v1 router.

Endpoints here are the default application API surface for the template.
"""

from __future__ import annotations

from fastapi import APIRouter

from app_name.main import __version__
from app_name.shared.schemas.response import APIResponse

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/health")
async def health() -> dict:
    """Versioned health check endpoint."""
    return APIResponse.ok(data={"status": "ok", "version": __version__}).model_dump()


# Include context-specific routers here:
# from app_name.contexts.some_context.interface.api.router import router as some_router
# router.include_router(some_router)
