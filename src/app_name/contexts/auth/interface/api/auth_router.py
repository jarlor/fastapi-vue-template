"""
Auth API router -- login, refresh, me, logout.

POST /login and POST /refresh are unauthenticated.
GET /me and POST /logout require a valid Bearer token.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app_name.api.deps import get_auth_service, require_auth
from app_name.contexts.auth.application.services.auth_service import AuthService
from app_name.contexts.auth.domain.entities import AuthPrincipal

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    account: str
    password_sha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfoResponse(BaseModel):
    user_id: str
    email: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate with account + hashed password."""
    try:
        tokens = await auth_service.login(body.account, body.password_sha)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a refresh token for a new token pair."""
    try:
        tokens = await auth_service.refresh_token(body.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserInfoResponse)
async def me(
    principal: Annotated[AuthPrincipal, Depends(require_auth)],
) -> UserInfoResponse:
    """Return the authenticated user's info."""
    return UserInfoResponse(user_id=principal.user_id, email=principal.email)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    principal: Annotated[AuthPrincipal, Depends(require_auth)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Revoke all refresh tokens for the authenticated user."""
    await auth_service.logout(principal.user_id)
    return MessageResponse(message="Logged out successfully")
