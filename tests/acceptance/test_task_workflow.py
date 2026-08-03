"""Human-owned acceptance oracle for the reference task workflow."""

from __future__ import annotations

from httpx import AsyncClient


async def test_user_can_create_and_list_a_task(test_client: AsyncClient) -> None:
    created = await test_client.post("/api/v1/tasks", json={"title": "Protect the acceptance boundary"})

    assert created.status_code == 201
    task = created.json()["data"]
    assert task["title"] == "Protect the acceptance boundary"
    assert task["completed"] is False

    listed = await test_client.get("/api/v1/tasks")

    assert listed.status_code == 200
    assert listed.json()["data"] == [task]


async def test_task_validation_uses_the_public_error_contract(test_client: AsyncClient) -> None:
    response = await test_client.post("/api/v1/tasks", json={"title": "   "})

    assert response.status_code == 422
    assert response.json() == {
        "code": 10000,
        "success": False,
        "data": None,
        "message": "body -> title: Value error, Task title cannot be blank",
    }
