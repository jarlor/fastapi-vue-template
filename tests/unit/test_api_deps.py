"""Tests for API dependency helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app_name.api.deps import _get_registry
from app_name.core.registry import AppRegistry
from app_name.shared.events.bus import InProcessEventBus


class TestGetRegistry:
    def test_returns_registry_from_request_state(self, test_settings) -> None:
        registry = AppRegistry(settings=test_settings, event_bus=InProcessEventBus())
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(registry=registry)))

        assert _get_registry(request) is registry

    def test_raises_503_when_registry_missing(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

        with pytest.raises(HTTPException) as exc:
            _get_registry(request)

        assert exc.value.status_code == 503
        assert exc.value.detail == "Application not ready"
