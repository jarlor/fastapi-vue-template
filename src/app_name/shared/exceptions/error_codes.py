"""Centralised error codes for the application.

Each domain context can define its own range:
- Common:  10000-10999
- Add context-specific error codes here (e.g., auth: 11000-11999)
"""

from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    # Common
    VALIDATION_ERROR = 10000
    UNKNOWN_ERROR = 10099

    @property
    def message(self) -> str:
        return _ERROR_MESSAGES.get(self, "Unknown error")


_ERROR_MESSAGES: dict[int, str] = {
    ErrorCode.VALIDATION_ERROR: "Parameter validation failed",
    ErrorCode.UNKNOWN_ERROR: "An unexpected error occurred",
}
