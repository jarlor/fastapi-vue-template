"""Root conftest -- shared fixtures for all tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app_name.config import Settings
from app_name.main import create_app


@pytest.fixture()
def mock_db() -> MagicMock:
    """A mock database handle for repository-level tests."""
    db = MagicMock()
    db.__getitem__.side_effect = lambda name: MagicMock(name=name)
    return db


@pytest.fixture()
def test_settings() -> Settings:
    """Safe settings object for tests without reading .env or config.yaml."""
    return Settings(
        app_name="app_name_test",
        debug=True,
        server={"host": "127.0.0.1", "port": 8665, "reload": False},
        cors={
            "allow_origins": ["http://localhost:8006"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
        frontend={"base_url": "http://localhost:8006"},
        logging={
            "level": "WARNING",
            "log_dir": "logs",
            "retention_days": 1,
            "error_retention_days": 1,
            "rotation": "00:00",
            "compression": "gz",
        },
    )


@pytest.fixture()
async def test_client(test_settings: Settings) -> AsyncClient:
    """An httpx AsyncClient bound to the FastAPI app."""
    app = create_app(settings=test_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
