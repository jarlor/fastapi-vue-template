"""Task aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    title: str
    completed: bool = False

    @classmethod
    def create(cls, title: str) -> Task:
        normalized = title.strip()
        if not normalized:
            raise ValueError("Task title cannot be blank")
        return cls(id=uuid4().hex, title=normalized)
