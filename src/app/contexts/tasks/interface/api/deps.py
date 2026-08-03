"""Task-specific FastAPI dependencies."""

from __future__ import annotations

from typing import Protocol, cast

from fastapi import HTTPException, Request, status

from app.contexts.tasks.application.services.task_service import TaskService


class TaskServiceProvider(Protocol):
    """Narrow view of the outer container required by this interface."""

    tasks: TaskService


def get_task_service(request: Request) -> TaskService:
    """Resolve only this context's application service from runtime state."""
    provider = getattr(request.app.state, "container", None)
    if provider is None or not hasattr(provider, "tasks"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready",
        )
    return cast(TaskServiceProvider, provider).tasks
