"""Generic API response envelope."""

from __future__ import annotations

from pydantic import BaseModel


class APIResponse[T](BaseModel):
    """Uniform JSON envelope for all API responses."""

    code: int = 0
    success: bool = True
    data: T | None = None
    message: str | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str = "OK") -> APIResponse[T]:
        return cls(code=0, success=True, data=data, message=message)

    @classmethod
    def error(cls, code: int, message: str) -> APIResponse[None]:
        return cls(code=code, success=False, data=None, message=message)
