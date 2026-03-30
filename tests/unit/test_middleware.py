"""Tests for request context middleware."""

from __future__ import annotations

from app_name.shared.middleware.request_context import (
    RequestContextMiddleware,
    get_request_id,
)


class TestRequestContext:
    async def test_request_id_generated(self) -> None:
        """Middleware should set a request_id in scope state."""
        captured_scope: dict = {}

        async def mock_app(scope, receive, send) -> None:  # noqa: ARG001
            captured_scope.update(scope)

        middleware = RequestContextMiddleware(mock_app)

        scope = {"type": "http", "state": {}}
        await middleware(scope, None, None)

        assert "request_id" in captured_scope["state"]
        assert len(captured_scope["state"]["request_id"]) > 0

    async def test_request_id_in_contextvar(self) -> None:
        """get_request_id() should return the current request's ID."""
        captured_id: str | None = None

        async def mock_app(scope, receive, send) -> None:  # noqa: ARG001
            nonlocal captured_id
            captured_id = get_request_id()

        middleware = RequestContextMiddleware(mock_app)

        scope = {"type": "http", "state": {}}
        await middleware(scope, None, None)

        assert captured_id is not None
        assert len(captured_id) > 0

    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP scopes should pass through without modification."""
        called = False

        async def mock_app(scope, receive, send) -> None:  # noqa: ARG001
            nonlocal called
            called = True

        middleware = RequestContextMiddleware(mock_app)

        scope = {"type": "lifespan"}
        await middleware(scope, None, None)

        assert called
