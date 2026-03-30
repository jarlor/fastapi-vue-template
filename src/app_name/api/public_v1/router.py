"""
Public API v1 router.

Endpoints here are accessible without authentication.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/public/v1", tags=["public"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Public health check endpoint."""
    return {"status": "ok"}


# Include context-specific public routers here:
# from app_name.contexts.some_context.interface.api.router import router as some_router
# router.include_router(some_router)
