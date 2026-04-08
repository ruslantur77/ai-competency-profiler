from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.candidate import CandidateAssessmentResultDTO
from competency_system.application.dtos.task import (
    CandidateTaskAssessmentDTO,
    SyncTasksResultDTO,
    TaskDTO,
    TaskSyncPeriodDTO,
)
from competency_system.application.use_cases.candidate import AssessCandidateUseCase
from competency_system.application.use_cases.task import (
    GetTaskUseCase,
    SyncTasksUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_assess_candidate_use_case,
    get_get_task_use_case,
    get_sync_tasks_use_case,
    require_admin_or_system,
    require_hr_expert_admin,
    verify_testing_system_webhook_secret,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/sync", response_model=SyncTasksResultDTO)
async def sync_tasks(
    payload: TaskSyncPeriodDTO,
    _: Annotated[None, Depends(require_admin_or_system)],
    use_case: Annotated[SyncTasksUseCase, Depends(get_sync_tasks_use_case)],
) -> SyncTasksResultDTO:
    return await use_case.execute(start=payload.start, end=payload.end)


@router.get("/{task_id}/mapping", response_model=TaskDTO)
async def get_task_mapping(
    task_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[GetTaskUseCase, Depends(get_get_task_use_case)],
) -> TaskDTO:
    try:
        return await use_case.execute(task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@webhook_router.post(
    "/task-completed",
    response_model=CandidateAssessmentResultDTO,
    dependencies=[Depends(verify_testing_system_webhook_secret)],
)
async def task_completed(
    payload: CandidateTaskAssessmentDTO,
    use_case: Annotated[AssessCandidateUseCase, Depends(get_assess_candidate_use_case)],
) -> CandidateAssessmentResultDTO:
    try:
        return await use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
