from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams

from competency_system.application.dtos.candidate import (
    CandidateListItemDto,
    CandidateProfileDTO,
)
from competency_system.application.use_cases.candidate import (
    DeleteCandidateUseCase,
    GetCandidateProfileUseCase,
    GetCandidateUseCase,
    ListCandidatesUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_delete_candidate_use_case,
    get_get_candidate_profile_use_case,
    get_get_candidate_use_case,
    get_list_candidates_use_case,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=LimitOffsetPage[CandidateListItemDto])
async def list_candidates(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[ListCandidatesUseCase, Depends(get_list_candidates_use_case)],
    params: Annotated[LimitOffsetParams, Depends()],
) -> LimitOffsetPage[CandidateListItemDto]:
    result = await use_case.execute(limit=params.limit, offset=params.offset)
    return LimitOffsetPage.create(
        items=result.items,
        total=result.total,
        params=params,
    )


@router.get("/{candidate_id}", response_model=CandidateListItemDto)
async def get_candidate(
    candidate_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[GetCandidateUseCase, Depends(get_get_candidate_use_case)],
) -> CandidateListItemDto:
    return await use_case.execute(candidate_id)


@router.get("/{candidate_id}/profile", response_model=CandidateProfileDTO)
async def get_candidate_profile(
    candidate_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetCandidateProfileUseCase,
        Depends(get_get_candidate_profile_use_case),
    ],
) -> CandidateProfileDTO:
    return await use_case.execute(candidate_id)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        DeleteCandidateUseCase,
        Depends(get_delete_candidate_use_case),
    ],
) -> None:
    await use_case.execute(candidate_id)
