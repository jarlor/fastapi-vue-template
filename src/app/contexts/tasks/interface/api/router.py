"""Task HTTP routes kept thin by delegating to the application service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.contexts.tasks.application.services.task_service import TaskService
from app.contexts.tasks.interface.api.deps import get_task_service
from app.contexts.tasks.interface.api.schemas import TaskCreate, TaskRead
from app.shared.schemas.response import APIResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse[TaskRead],
    responses={422: {"model": APIResponse[None], "description": "Validation error"}},
)
async def create_task(
    payload: TaskCreate,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> APIResponse[TaskRead]:
    task = await service.create(payload.title)
    return APIResponse.ok(data=TaskRead.model_validate(task))


@router.get("", response_model=APIResponse[list[TaskRead]])
async def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
) -> APIResponse[list[TaskRead]]:
    tasks = await service.list()
    return APIResponse.ok(data=[TaskRead.model_validate(task) for task in tasks])
