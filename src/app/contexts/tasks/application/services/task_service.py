"""Task use cases."""

from __future__ import annotations

from collections.abc import Sequence

from app.contexts.tasks.application.ports.task_repository import TaskRepository
from app.contexts.tasks.domain.task import Task


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create(self, title: str) -> Task:
        task = Task.create(title)
        await self._repository.add(task)
        return task

    async def list(self) -> Sequence[Task]:
        return await self._repository.list()
