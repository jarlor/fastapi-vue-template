"""Root conftest -- shared fixtures for all tests."""

from __future__ import annotations

import os

# Set required env vars BEFORE any application imports so pydantic-settings
# never fails during test collection.
os.environ.setdefault("AUTH__SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGODB__URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB__DATABASE", "app_name_test")

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture()
def mock_db() -> MagicMock:
    """A mock Motor database.

    Accessing ``mock_db["collection_name"]`` returns a ``MagicMock`` with
    common async operations pre-stubbed (find_one, insert_one, etc.).
    """
    db = MagicMock()

    def _make_collection(name: str) -> MagicMock:
        col = MagicMock(name=f"mock_{name}")
        col.find_one = AsyncMock(return_value=None)
        col.insert_one = AsyncMock()
        col.update_one = AsyncMock()
        col.delete_one = AsyncMock()
        col.count_documents = AsyncMock(return_value=0)

        # find() returns a cursor-like object
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[])
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.sort = MagicMock(return_value=cursor)
        col.find = MagicMock(return_value=cursor)

        return col

    db.__getitem__ = MagicMock(side_effect=_make_collection)
    return db


@pytest.fixture()
def test_settings() -> dict:
    """Safe settings dict for unit tests."""
    return {
        "mongodb": {
            "url": "mongodb://localhost:27017",
            "database": "app_name_test",
        },
        "auth": {
            "secret_key": "test-secret-key-not-for-production",
            "access_token_minutes": 60,
            "refresh_token_days": 1,
        },
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
