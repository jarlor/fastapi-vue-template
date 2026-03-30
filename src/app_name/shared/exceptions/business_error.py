"""Business error -- the single application-level exception type.

Raise ``BusinessError(ErrorCode.SOME_CODE)`` anywhere in service or API code.
The global exception handler converts it into a structured JSON response.
"""

from __future__ import annotations

from app_name.shared.exceptions.error_codes import ErrorCode


class BusinessError(Exception):
    """Structured business error carrying an ``ErrorCode`` and optional message."""

    def __init__(self, code: ErrorCode | int, message: str | None = None) -> None:
        self.code = int(code)
        self.message = message or (code.message if isinstance(code, ErrorCode) else "Unknown error")
        super().__init__(self.message)
