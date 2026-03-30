"""
Auth service -- JWT-based authentication implementation.

Uses PyJWT for token creation and verification.
User credentials are stored in a ``users`` MongoDB collection.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from loguru import logger

from app_name.config import Settings
from app_name.contexts.auth.domain.entities import AuthPrincipal
from app_name.database.mongo import MongoDBManager


class AuthService:
    """Concrete auth service backed by MongoDB + PyJWT."""

    def __init__(self, *, db: MongoDBManager, settings: Settings) -> None:
        self._users = db.get_collection("users")
        self._refresh_tokens = db.get_collection("refresh_tokens")
        self._secret = settings.auth.jwt_secret
        self._algorithm = settings.auth.jwt_algorithm
        self._access_minutes = settings.auth.access_token_expire_minutes
        self._refresh_days = settings.auth.refresh_token_expire_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def login(self, account: str, password_sha: str) -> dict[str, str]:
        """Authenticate a user by account + SHA-hashed password.

        Returns:
            Dict with ``access_token`` and ``refresh_token``.

        Raises:
            ValueError: If credentials are invalid.
        """
        user = await self._users.find_one(
            {"account": account, "password_sha": password_sha}
        )
        if user is None:
            raise ValueError("Invalid credentials")

        user_id = str(user["_id"])
        email = user.get("email", "")

        access_token = self._create_token(
            user_id=user_id,
            email=email,
            token_type="access",
            expires_delta=timedelta(minutes=self._access_minutes),
        )
        refresh_token = self._create_token(
            user_id=user_id,
            email=email,
            token_type="refresh",
            expires_delta=timedelta(days=self._refresh_days),
        )

        # Persist refresh token for revocation support
        await self._refresh_tokens.insert_one(
            {
                "user_id": user_id,
                "token": refresh_token,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return {"access_token": access_token, "refresh_token": refresh_token}

    async def resolve_access_token(self, token: str) -> AuthPrincipal | None:
        """Decode an access token and return the AuthPrincipal, or None."""
        payload = self._decode_token(token)
        if payload is None or payload.get("type") != "access":
            return None
        return AuthPrincipal(
            user_id=payload["sub"],
            email=payload.get("email", ""),
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Exchange a valid refresh token for a new token pair.

        Raises:
            ValueError: If the refresh token is invalid or revoked.
        """
        payload = self._decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        # Verify token exists in the database (not revoked)
        stored = await self._refresh_tokens.find_one({"token": refresh_token})
        if stored is None:
            raise ValueError("Refresh token revoked")

        user_id = payload["sub"]
        email = payload.get("email", "")

        # Rotate: delete old, issue new pair
        await self._refresh_tokens.delete_one({"token": refresh_token})

        new_access = self._create_token(
            user_id=user_id,
            email=email,
            token_type="access",
            expires_delta=timedelta(minutes=self._access_minutes),
        )
        new_refresh = self._create_token(
            user_id=user_id,
            email=email,
            token_type="refresh",
            expires_delta=timedelta(days=self._refresh_days),
        )

        await self._refresh_tokens.insert_one(
            {
                "user_id": user_id,
                "token": new_refresh,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return {"access_token": new_access, "refresh_token": new_refresh}

    async def logout(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        result = await self._refresh_tokens.delete_many({"user_id": user_id})
        logger.info("Revoked {} refresh tokens for user {}", result.deleted_count, user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_token(
        self,
        *,
        user_id: str,
        email: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": user_id,
            "email": email,
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def _decode_token(self, token: str) -> dict[str, Any] | None:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError:
            return None
