"""Tests for error codes, business errors, and API response."""

from __future__ import annotations

from app.shared.exceptions.error_codes import ErrorCode
from app.shared.schemas.response import APIResponse


class TestErrorCode:
    def test_error_codes_have_messages(self) -> None:
        for code in ErrorCode:
            assert isinstance(code.message, str)
            assert len(code.message) > 0

    def test_specific_codes(self) -> None:
        assert ErrorCode.VALIDATION_ERROR == 10000
        assert ErrorCode.UNKNOWN_ERROR == 10099

    def test_message_property(self) -> None:
        assert "validation" in ErrorCode.VALIDATION_ERROR.message.lower()


class TestAPIResponse:
    def test_ok(self) -> None:
        resp = APIResponse.ok(data={"id": "1"})
        assert resp.code == 0
        assert resp.success is True
        assert resp.data == {"id": "1"}
        assert resp.message == "OK"

    def test_ok_no_data(self) -> None:
        resp = APIResponse.ok()
        assert resp.success is True
        assert resp.data is None
        assert resp.message == "OK"

    def test_error(self) -> None:
        resp = APIResponse.error(code=10099, message="unexpected")
        assert resp.code == 10099
        assert resp.success is False
        assert resp.message == "unexpected"
        assert resp.data is None

    def test_serialization(self) -> None:
        resp = APIResponse.ok(data={"key": "value"})
        d = resp.model_dump()
        assert d["code"] == 0
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["message"] == "OK"
