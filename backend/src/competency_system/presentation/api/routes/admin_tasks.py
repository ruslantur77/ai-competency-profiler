from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from competency_system.application.dtos.task import TaskDTO
from competency_system.application.use_cases.task import (
    GetTaskUseCase,
    ListTasksUseCase,
    RebuildTaskMappingUseCase,
    ValidateTaskMappingUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_get_task_use_case,
    get_list_tasks_use_case,
    get_rebuild_task_mapping_use_case,
    get_validate_task_mapping_use_case,
    require_admin_or_expert,
)

router = APIRouter(
    prefix="/admin/tasks",
    tags=["admin-tasks"],
    dependencies=[Depends(require_admin_or_expert)],
)


@router.get("", response_model=list[TaskDTO])
async def list_tasks(
    use_case: Annotated[ListTasksUseCase, Depends(get_list_tasks_use_case)],
) -> list[TaskDTO]:
    return await use_case.execute()


@router.get("/{task_id}", response_model=TaskDTO)
async def get_task(
    task_id: UUID,
    use_case: Annotated[GetTaskUseCase, Depends(get_get_task_use_case)],
) -> TaskDTO:
    return await use_case.execute(task_id)


@router.post("/{task_id}/mapping/rebuild", response_model=TaskDTO)
async def rebuild_task_mapping(
    task_id: UUID,
    use_case: Annotated[
        RebuildTaskMappingUseCase,
        Depends(get_rebuild_task_mapping_use_case),
    ],
) -> TaskDTO:
    return await use_case.execute(task_id)


@router.post("/{task_id}/mapping/validate", response_model=TaskDTO)
async def validate_task_mapping(
    task_id: UUID,
    use_case: Annotated[
        ValidateTaskMappingUseCase,
        Depends(get_validate_task_mapping_use_case),
    ],
) -> TaskDTO:
    return await use_case.execute(task_id)
