"""
In-process event bus for decoupled domain event communication.

Handlers are async callables; failures in one handler do not affect others.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

# Type alias for event handler functions
EventHandler = Callable[[Any], Awaitable[None]]


class InProcessEventBus:
    """Simple pub/sub event bus running handlers concurrently via asyncio."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Register a handler for a given event type."""
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed {} to {}", handler.__qualname__, event_type.__name__)

    async def publish(self, event: Any, *, timeout: float = 30.0) -> None:
        """Publish an event to all registered handlers.

        Each handler runs with its own timeout. Exceptions are logged
        but do not propagate -- they never block other handlers.

        Args:
            event: The event instance to dispatch.
            timeout: Per-handler timeout in seconds.
        """
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return

        async def _safe_call(handler: EventHandler) -> None:
            try:
                await asyncio.wait_for(handler(event), timeout=timeout)
            except asyncio.TimeoutError:
                logger.error(
                    "Handler {} timed out after {:.1f}s for {}",
                    handler.__qualname__,
                    timeout,
                    type(event).__name__,
                )
            except Exception:
                logger.exception(
                    "Handler {} raised an exception for {}",
                    handler.__qualname__,
                    type(event).__name__,
                )

        await asyncio.gather(*(_safe_call(h) for h in handlers))
