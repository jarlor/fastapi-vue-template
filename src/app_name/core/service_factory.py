"""
Service factory -- builds the AppRegistry during startup.

All cross-cutting wiring (event bus, service factories, event subscriptions)
is centralised here so that ``main.py`` stays clean.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app_name.core.registry import AppRegistry
from app_name.shared.events.bus import InProcessEventBus

if TYPE_CHECKING:
    from app_name.config import Settings


def build_registry(*, settings: Settings) -> AppRegistry:
    """Construct the registry with all service factories and event wiring."""

    event_bus = InProcessEventBus()

    # --- Add context-specific service factories here ---
    # Keep provider SDKs and external I/O in infrastructure adapters/gateways.
    # Application services should receive ports, not concrete SDK clients.
    #
    # Example:
    #   from functools import partial
    #   from app_name.contexts.chat.application.services.chat_service import ChatService
    #   from app_name.contexts.chat.infrastructure.gateways.provider_chat_gateway import ProviderChatGateway
    #
    #   chat_model_factory = partial(ProviderChatGateway, settings=settings)
    #   chat_service_factory = lambda: ChatService(model=chat_model_factory())

    # --- Register domain event handlers ---
    # Example:
    #   from app_name.contexts.some_context.application.services import handler
    #   event_bus.subscribe(SomeEvent, handler)

    registry = AppRegistry(
        settings=settings,
        event_bus=event_bus,
    )

    logger.info("AppRegistry built successfully")
    return registry
