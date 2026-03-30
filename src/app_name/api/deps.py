"""
FastAPI dependency injection providers.

All request-scoped dependencies are resolved here from the AppRegistry
stored on ``app.state.registry``.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

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


# Add your context-specific dependencies here, e.g.:
#
# def get_my_service(
#     registry: Annotated[AppRegistry, Depends(_get_registry)],
# ) -> MyService:
#     if registry.my_service_factory is None:
#         raise HTTPException(status_code=503, detail="Service not configured")
#     return registry.my_service_factory()
