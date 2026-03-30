"""Request context middleware -- assigns a unique request_id to every request.

The request_id is stored in both ``scope["state"]["request_id"]`` and a
``contextvars.ContextVar`` so it can be accessed from any async code path.
"""

from __future__ import annotations

import contextvars
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from app_name.shared.middleware.base import BaseASGIMiddleware

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="",
)


def get_request_id() -> str:
    """Return the current request_id (empty string outside a request)."""
    return _request_id_ctx.get()


class RequestContextMiddleware(BaseASGIMiddleware):
    """Generate a UUID request_id and propagate it via scope state and contextvars."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def process(self, scope: Scope, receive: Receive, send: Send) -> None:
        request_id = uuid.uuid4().hex

        # Store in ASGI scope state (accessible from Request.state)
        state: dict = scope.setdefault("state", {})
        state["request_id"] = request_id

        # Store in contextvar for async propagation
        token = _request_id_ctx.set(request_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _request_id_ctx.reset(token)
