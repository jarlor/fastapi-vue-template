"""Transport-level error codes shared by the HTTP exception handlers.

Context-specific errors remain owned by their context and are translated at
the interface boundary; they do not accumulate in this module.
"""

from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    """Stable codes for cross-cutting request and server failures only."""

    VALIDATION_ERROR = 10000
    UNKNOWN_ERROR = 10099

    @property
    def message(self) -> str:
        return _ERROR_MESSAGES.get(self, "Unknown error")


_ERROR_MESSAGES: dict[int, str] = {
    ErrorCode.VALIDATION_ERROR: "Parameter validation failed",
    ErrorCode.UNKNOWN_ERROR: "An unexpected error occurred",
}
