"""
Application registry -- central holder for shared infrastructure and service factories.

Every request-scoped dependency pulls what it needs from this registry
(stored at ``app.state.registry``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app_name.config import Settings
    from app_name.shared.events.bus import InProcessEventBus


@dataclass(slots=True)
class AppRegistry:
    """Immutable-ish container wired up once during startup."""

    settings: Settings
    event_bus: InProcessEventBus

    # Service factories -- use ``functools.partial`` for lazy creation.
    # Add your context-specific factories here, e.g.:
    # example_service_factory: Callable[..., Any] | None = None
