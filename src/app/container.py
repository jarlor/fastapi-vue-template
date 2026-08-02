"""Typed dependencies exposed by the composition root."""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts.tasks.application.services.task_service import TaskService


@dataclass(slots=True)
class AppContainer:
    """Application services available to transport adapters."""

    tasks: TaskService
