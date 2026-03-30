"""Tests for global exception handlers."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.exceptions import RequestValidationError

from app_name.shared.exceptions.business_error import BusinessError
from app_name.shared.exceptions.error_codes import ErrorCode
from app_name.shared.exceptions.handlers import (
    business_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)


class TestExceptionHandlers:
    async def test_business_error_handler_returns_api_envelope(self) -> None:
        response = await business_error_handler(
            MagicMock(),
            BusinessError(ErrorCode.VALIDATION_ERROR, "bad input"),
        )

        assert response.status_code == 200
        assert response.body == b'{"code":10000,"success":false,"data":null,"message":"bad input"}'

    async def test_validation_error_handler_returns_api_envelope(self) -> None:
        exc = RequestValidationError(
            [
                {
                    "type": "missing",
                    "loc": ("body", "email"),
                    "msg": "Field required",
                    "input": None,
                }
            ]
        )

        response = await validation_error_handler(MagicMock(), exc)

        assert response.status_code == 422
        assert b'"code":10000' in response.body
        assert b'"success":false' in response.body
        assert b'body -> email: Field required' in response.body

    async def test_unhandled_error_handler_hides_internal_details(self) -> None:
        response = await unhandled_error_handler(MagicMock(), RuntimeError("boom"))

        assert response.status_code == 500
        assert response.body == (
            b'{"code":10099,"success":false,"data":null,"message":"An unexpected error occurred"}'
        )
