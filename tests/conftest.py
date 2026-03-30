"""Root conftest -- shared fixtures for all tests."""

from __future__ import annotations

import pytest


@pytest.fixture()
def test_settings() -> dict:
    """Safe settings dict for unit tests."""
    return {
        "server": {
            "host": "127.0.0.1",
            "port": 8665,
            "reload": False,
        },
    }


@pytest.fixture()
async def test_client():
    """An httpx AsyncClient bound to the FastAPI app.

    Override this fixture once the app factory is implemented:

        from httpx import ASGITransport, AsyncClient
        from app_name.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    """
    pytest.skip("Implement test_client once the app factory exists.")
