"""Shared product-test fixtures."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def test_settings() -> Settings:
    return Settings(
        app_name="Test App",
        debug=True,
        server={"host": "127.0.0.1", "port": 8665, "reload": False},
        cors={"allow_origins": ["http://localhost:5173"]},
        frontend={"base_url": "http://localhost:5173"},
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
    app = create_app(settings=test_settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client,
    ):
        yield client
