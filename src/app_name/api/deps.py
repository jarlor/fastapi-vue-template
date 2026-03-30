"""
FastAPI dependency injection providers.

All request-scoped dependencies are resolved here from the AppRegistry
stored on ``app.state.registry``.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app_name.contexts.auth.application.services.auth_service import AuthService
from app_name.contexts.auth.domain.entities import AuthPrincipal
from app_name.core.registry import AppRegistry


def _get_registry(request: Request) -> AppRegistry:
    """Extract the AppRegistry from the current application state."""
    registry: AppRegistry | None = getattr(request.app.state, "registry", None)
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready",
        )
    return registry


def get_auth_service(
    registry: Annotated[AppRegistry, Depends(_get_registry)],
) -> AuthService:
    """Provide an AuthService instance from the registry factory."""
    if registry.auth_service_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured",
        )
    return registry.auth_service_factory()


def get_bearer_token(request: Request) -> str:
    """Extract a Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header.removeprefix("Bearer ").strip()


async def require_auth(
    token: Annotated[str, Depends(get_bearer_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthPrincipal:
    """Verify JWT and return the authenticated principal."""
    principal = await auth_service.resolve_access_token(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal
