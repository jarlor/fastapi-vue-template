"""Tests for concrete composition, logging, runner, and time helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from app import run_api
from app.bootstrap import build_container
from app.contexts.tasks.application.services.task_service import TaskService
from app.core import logging as logging_module
from app.core.timezone import now_local, now_utc, to_local


def test_container_wires_a_real_task_service() -> None:
    assert isinstance(build_container().tasks, TaskService)


def test_setup_logging_configures_console_and_file_handlers(tmp_path, monkeypatch) -> None:
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


def test_run_api_uses_uvicorn_factory_mode(monkeypatch, test_settings) -> None:
    run = MagicMock()
    monkeypatch.setattr(run_api, "get_settings", lambda: test_settings)
    monkeypatch.setattr(run_api.uvicorn, "run", run)

    run_api.main()

    run.assert_called_once_with(
        "app.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8665,
        reload=False,
        log_level="warning",
    )


def test_timezone_helpers_return_aware_datetimes() -> None:
    utc_now = now_utc()
    local_now = now_local()

    assert utc_now.tzinfo is UTC
    assert local_now.tzinfo is not None
    assert to_local(datetime(2026, 1, 1, tzinfo=UTC), ZoneInfo("Asia/Shanghai")).utcoffset() is not None
