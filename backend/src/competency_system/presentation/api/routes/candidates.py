from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.candidate import CandidateProfileDTO
from competency_system.application.use_cases.candidate import GetCandidateProfileUseCase
from competency_system.presentation.api.dependencies import (
    get_get_candidate_profile_use_case,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/{candidate_id}/profile", response_model=CandidateProfileDTO)
async def get_candidate_profile(
    candidate_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetCandidateProfileUseCase,
        Depends(get_get_candidate_profile_use_case),
    ],
) -> CandidateProfileDTO:
    try:
        return await use_case.execute(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
