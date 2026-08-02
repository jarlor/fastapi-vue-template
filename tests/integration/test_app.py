"""Integration tests for application wiring and stable runtime contracts."""

from __future__ import annotations

from httpx import AsyncClient

from app.api.v1.router import router as v1_router
from app.main import create_app


async def test_root_health_contract(test_client: AsyncClient) -> None:
    response = await test_client.get("/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["status"] == "ok"


async def test_versioned_health_contract(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_lifespan_keeps_injected_dependencies(test_settings) -> None:
    app = create_app(settings=test_settings)

    async with app.router.lifespan_context(app):
        assert app.state.settings is test_settings
        assert app.state.container.tasks is not None


def test_v1_router_uses_single_prefix() -> None:
    assert v1_router.prefix == "/api/v1"


def test_task_validation_openapi_matches_public_error_envelope() -> None:
    schema = create_app().openapi()

    validation_schema = schema["paths"]["/api/v1/tasks"]["post"]["responses"]["422"]["content"]["application/json"][
        "schema"
    ]

    assert validation_schema == {"$ref": "#/components/schemas/APIResponse_NoneType_"}
    assert "422" not in schema["paths"]["/api/v1/tasks"]["get"]["responses"]
