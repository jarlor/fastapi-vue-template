"""In-memory task repository used by the runnable baseline."""

from __future__ import annotations

from collections.abc import Sequence

from app.contexts.tasks.domain.task import Task


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    async def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def list(self) -> Sequence[Task]:
        return tuple(self._tasks.values())
