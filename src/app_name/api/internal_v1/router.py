"""
Internal API v1 router.

Endpoints here are for authenticated / back-office operations.
"""
from __future__ import annotations

from fastapi import APIRouter

from app_name.contexts.auth.interface.api.auth_router import router as auth_router

router = APIRouter(prefix="/api/internal/v1", tags=["internal"])

# Auth routes (login/refresh don't require auth themselves)
router.include_router(auth_router)

# Protected routers -- add Depends(require_auth) at the router or endpoint level:
# from app_name.api.deps import require_auth
# from app_name.contexts.some_context.interface.api.router import router as some_router
# router.include_router(some_router, dependencies=[Depends(require_auth)])
