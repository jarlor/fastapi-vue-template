"""
Service factory -- builds the AppRegistry during startup.

All cross-cutting wiring (event bus, service factories, event subscriptions)
is centralised here so that ``main.py`` stays clean.
"""
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from loguru import logger

from app_name.core.registry import AppRegistry
from app_name.shared.events.bus import InProcessEventBus

if TYPE_CHECKING:
    from app_name.config import Settings
    from app_name.database.mongo import MongoDBManager


async def build_registry(
    *,
    db: MongoDBManager,
    settings: Settings,
) -> AppRegistry:
    """Construct the registry with all service factories and event wiring."""

    event_bus = InProcessEventBus()

    # --- Auth service factory (lazy, created per-request via partial) ---
    from app_name.contexts.auth.application.services.auth_service import AuthService

    auth_service_factory = partial(AuthService, db=db, settings=settings)

    # --- Register domain event handlers ---
    # Example:
    #   from app_name.contexts.some_context.application.services import handler
    #   event_bus.subscribe(SomeEvent, handler)

    registry = AppRegistry(
        db=db,
        settings=settings,
        event_bus=event_bus,
        auth_service_factory=auth_service_factory,
    )

    logger.info("AppRegistry built successfully")
    return registry
