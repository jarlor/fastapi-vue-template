"""Auth domain entities."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """Represents an authenticated user identity extracted from a JWT."""

    user_id: str
    email: str
