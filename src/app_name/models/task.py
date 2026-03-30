"""
Generic task run model for tracking background/pipeline operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskRun:
    """Represents a single background task execution."""

    task_id: str = field(default_factory=lambda: uuid4().hex)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_mongo_dict(self) -> dict[str, Any]:
        """Serialise to a MongoDB-friendly dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_mongo_dict(cls, data: dict[str, Any]) -> TaskRun:
        """Deserialise from a MongoDB document."""
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )
