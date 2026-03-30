"""
Auth port -- protocol defining the auth service contract.

Implement this protocol to swap authentication backends
(e.g., database-backed, OAuth, LDAP).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app_name.contexts.auth.domain.entities import AuthPrincipal


@runtime_checkable
class AuthPort(Protocol):
    """Abstract contract for authentication operations."""

    async def login(self, account: str, password_sha: str) -> dict[str, str]:
        """Authenticate and return access + refresh tokens."""
        ...

    async def resolve_access_token(self, token: str) -> AuthPrincipal | None:
        """Decode and validate an access token, returning the principal."""
        ...

    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Exchange a refresh token for new access + refresh tokens."""
        ...

    async def logout(self, user_id: str) -> None:
        """Invalidate all tokens for the given user."""
        ...
