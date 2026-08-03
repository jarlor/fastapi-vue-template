"""Focused tests for the reference bounded context."""

from __future__ import annotations

import pytest

from app.contexts.tasks.application.services.task_service import TaskService
from app.contexts.tasks.domain.task import Task
from app.contexts.tasks.infrastructure.repositories.in_memory import InMemoryTaskRepository


def test_domain_normalizes_title() -> None:
    assert Task.create("  ship it  ").title == "ship it"


def test_domain_rejects_blank_title() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        Task.create("   ")


async def test_service_persists_through_a_port() -> None:
    service = TaskService(repository=InMemoryTaskRepository())

    created = await service.create("Keep boundaries executable")

    assert list(await service.list()) == [created]
