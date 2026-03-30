"""Base ASGI middleware class for pure ASGI middleware implementations."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class BaseASGIMiddleware:
    """Abstract base for pure ASGI middleware.

    Subclasses override ``process()`` to handle HTTP and WebSocket requests.
    Non-HTTP/WS scopes (e.g. ``lifespan``) are passed through untouched.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        await self.process(scope, receive, send)

    async def process(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Override in subclasses."""
        await self.app(scope, receive, send)
