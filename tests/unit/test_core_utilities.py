"""Tests for service factory, logging, runner, timezone, and shared models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from app_name.core import logging as logging_module
from app_name.core.service_factory import build_registry
from app_name.core.timezone import now_local, now_utc, to_local
from app_name.models.task import TaskRun, TaskStatus
from app_name.run_api import main as run_api_main
from app_name.shared.events.bus import InProcessEventBus
from app_name.shared.events.models import ExampleEvent


class TestCoreUtilities:
    def test_build_registry_wires_settings_and_event_bus(self, test_settings) -> None:
        registry = build_registry(settings=test_settings)

        assert registry.settings is test_settings
        assert isinstance(registry.event_bus, InProcessEventBus)

    def test_setup_logging_configures_console_and_file_handlers(self, tmp_path, monkeypatch) -> None:
        remove = MagicMock()
        add = MagicMock()
        info = MagicMock()
        monkeypatch.setattr(logging_module.logger, "remove", remove)
        monkeypatch.setattr(logging_module.logger, "add", add)
        monkeypatch.setattr(logging_module.logger, "info", info)

        config = SimpleNamespace(
            level="warning",
            log_dir=str(tmp_path / "logs"),
            retention_days=7,
            error_retention_days=14,
            rotation="00:00",
            compression="gz",
        )

        logging_module.setup_logging(config)

        remove.assert_called_once()
        assert add.call_count == 3
        assert Path(config.log_dir).exists()
        info.assert_called_once()

    def test_run_api_uses_uvicorn_factory_mode(self, monkeypatch, test_settings) -> None:
        run = MagicMock()
        monkeypatch.setattr("app_name.run_api.get_settings", lambda: test_settings)
        monkeypatch.setattr("app_name.run_api.uvicorn.run", run)

        run_api_main()

        run.assert_called_once_with(
            "app_name.main:create_app",
            factory=True,
            host="127.0.0.1",
            port=8665,
            reload=False,
            log_level="warning",
        )

    def test_timezone_helpers_return_aware_datetimes(self) -> None:
        utc_now = now_utc()
        local_now = now_local()

        assert utc_now.tzinfo is UTC
        assert local_now.tzinfo is not None

        converted = to_local(datetime(2026, 1, 1, tzinfo=UTC), ZoneInfo("Asia/Shanghai"))
        assert converted.utcoffset() is not None

    def test_task_run_round_trips_to_mongo_dict(self) -> None:
        task = TaskRun(
            task_id="task-1",
            status=TaskStatus.RUNNING,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
            error=None,
            metadata={"step": 1},
        )

        serialized = task.to_mongo_dict()
        restored = TaskRun.from_mongo_dict(serialized)

        assert serialized["status"] == "running"
        assert restored == task

    def test_example_event_has_timestamp(self) -> None:
        event = ExampleEvent(entity_id="1", action="created")

        assert event.entity_id == "1"
        assert event.action == "created"
        assert isinstance(event.occurred_at, datetime)
