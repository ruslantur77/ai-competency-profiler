from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams

from competency_system.application.dtos.candidate import CandidateAssessmentResultDTO
from competency_system.application.dtos.task import (
    CandidateTaskAssessmentDTO,
    SyncTasksResultDTO,
    TaskDTO,
    TaskGraphUpdateDTO,
    TaskListItemDTO,
    TaskStatusUpdateDTO,
    TaskSyncRequestDTO,
)
from competency_system.application.use_cases.candidate import AssessCandidateUseCase
from competency_system.application.use_cases.task import (
    FinalizeTaskGraphUseCase,
    GetTaskGraphUseCase,
    ListTasksUseCase,
    SaveTaskGraphUseCase,
    SyncTasksUseCase,
    UpdateTaskStatusUseCase,
)
from competency_system.domain.value_objects.enums import TaskStatus
from competency_system.presentation.api.dependencies import (
    get_assess_candidate_use_case,
    get_finalize_task_graph_use_case,
    get_get_task_graph_use_case,
    get_list_tasks_use_case,
    get_save_task_graph_use_case,
    get_sync_tasks_use_case,
    get_update_task_status_use_case,
    require_admin_or_expert,
    require_admin_or_system,
    require_hr_expert_admin,
    verify_testing_system_webhook_secret,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/sync", response_model=SyncTasksResultDTO)
async def sync_tasks(
    payload: TaskSyncRequestDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[SyncTasksUseCase, Depends(get_sync_tasks_use_case)],
) -> SyncTasksResultDTO:
    return await use_case.execute(
        start=payload.start,
        end=payload.end,
        force=payload.force,
    )


@router.get("", response_model=LimitOffsetPage[TaskListItemDTO])
async def list_tasks(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[ListTasksUseCase, Depends(get_list_tasks_use_case)],
    params: Annotated[LimitOffsetParams, Depends()],
    status_filter: Annotated[list[TaskStatus] | None, Query()] = None,
) -> LimitOffsetPage[TaskListItemDTO]:
    statuses = set(status_filter) if status_filter else None
    result = await use_case.execute(
        statuses=statuses,
        limit=params.limit,
        offset=params.offset,
    )
    return LimitOffsetPage.create(
        items=result.items,
        total=result.total,
        params=params,
    )


@router.get("/{task_id}", response_model=TaskDTO)
async def get_task(
    task_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[GetTaskGraphUseCase, Depends(get_get_task_graph_use_case)],
) -> TaskDTO:
    return await use_case.execute(task_id)


@router.patch("/{task_id}/graph", response_model=TaskDTO)
async def save_task_graph(
    task_id: UUID,
    payload: TaskGraphUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[SaveTaskGraphUseCase, Depends(get_save_task_graph_use_case)],
) -> TaskDTO:
    return await use_case.execute(task_id, payload)


@router.post("/{task_id}/graph/finalize", response_model=TaskDTO)
async def finalize_task_graph(
    task_id: UUID,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        FinalizeTaskGraphUseCase,
        Depends(get_finalize_task_graph_use_case),
    ],
) -> TaskDTO:
    return await use_case.execute(task_id)


@router.patch("/{task_id}/status", response_model=TaskDTO)
async def update_task_status(
    task_id: UUID,
    payload: TaskStatusUpdateDTO,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        UpdateTaskStatusUseCase,
        Depends(get_update_task_status_use_case),
    ],
) -> TaskDTO:
    return await use_case.execute(task_id, payload)


@webhook_router.post(
    "/task-completed",
    response_model=CandidateAssessmentResultDTO,
    dependencies=[Depends(verify_testing_system_webhook_secret)],
)
async def task_completed(
    payload: CandidateTaskAssessmentDTO,
    use_case: Annotated[AssessCandidateUseCase, Depends(get_assess_candidate_use_case)],
) -> CandidateAssessmentResultDTO:
    return await use_case.execute(payload)
