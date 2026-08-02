"""Application dependency composition.

Concrete adapters are selected here. Domain and application modules never
reach into this module, which keeps dependency direction visible and testable.
"""

from __future__ import annotations

from app.container import AppContainer
from app.contexts.tasks.application.services.task_service import TaskService
from app.contexts.tasks.infrastructure.repositories.in_memory import InMemoryTaskRepository


def build_container() -> AppContainer:
    """Wire the default adapters used by this template."""
    return AppContainer(tasks=TaskService(repository=InMemoryTaskRepository()))
