"""Integration tests for application wiring and baseline routes."""

from __future__ import annotations

from httpx import AsyncClient

from app_name.api.v1.router import router as v1_router
from app_name.main import create_app


class TestHealthEndpoints:
    async def test_root_health_returns_api_envelope(
        self,
        test_client: AsyncClient,
    ) -> None:
        response = await test_client.get("/health")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["message"] == "OK"
        assert response.json()["data"]["status"] == "ok"

    async def test_versioned_health_returns_api_envelope(
        self,
        test_client: AsyncClient,
    ) -> None:
        response = await test_client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["message"] == "OK"
        assert response.json()["data"]["status"] == "ok"


class TestApplicationLifespan:
    async def test_lifespan_uses_injected_settings(self, test_settings) -> None:
        app = create_app(settings=test_settings)

        async with app.router.lifespan_context(app):
            assert app.state.registry.settings is test_settings


def test_v1_router_uses_single_prefix() -> None:
    assert v1_router.prefix == "/api/v1"
    assert not v1_router.dependencies
