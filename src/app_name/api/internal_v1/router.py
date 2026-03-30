"""
Internal API v1 router.

Endpoints here are for authenticated / back-office operations.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/internal/v1", tags=["internal"])

# Add your protected routes here, e.g.:
# from app_name.api.deps import require_auth
# from app_name.contexts.some_context.interface.api.router import router as some_router
# router.include_router(some_router, dependencies=[Depends(require_auth)])
