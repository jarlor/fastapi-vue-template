"""Persistence port owned by the task application layer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.contexts.tasks.domain.task import Task


class TaskRepository(Protocol):
    async def add(self, task: Task) -> None: ...

    async def list(self) -> Sequence[Task]: ...
