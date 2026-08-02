"""Tests for application dependency lookup."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.bootstrap import build_container
from app.contexts.tasks.interface.api.deps import get_task_service


def test_returns_task_service_from_app_state() -> None:
    container = build_container()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=container)))

    assert get_task_service(request) is container.tasks


def test_missing_container_is_service_unavailable() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as exc:
        get_task_service(request)

    assert exc.value.status_code == 503
