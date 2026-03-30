"""
Domain event base models.

All domain events should be frozen dataclasses with an ``occurred_at`` field.
Subscribe to them via the InProcessEventBus in ``bus.py``.

How to add a new domain event:
1. Define a frozen dataclass here (or in the relevant context's domain layer).
2. Publish it from your service: ``await event_bus.publish(MyEvent(...))``
3. Subscribe a handler in ``core/service_factory.py`` during startup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class ExampleEvent:
    """Example domain event -- replace or remove in your project."""

    entity_id: str
    action: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
