from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from competency_system.application.dtos.ranking import VacancyRankingDTO
from competency_system.application.use_cases.ranking import GetVacancyRankingUseCase
from competency_system.presentation.api.dependencies import (
    get_get_vacancy_ranking_use_case,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/vacancies", tags=["ranking"])


@router.get("/{vacancy_id}/rankings", response_model=VacancyRankingDTO)
async def get_vacancy_rankings(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyRankingUseCase, Depends(get_get_vacancy_ranking_use_case)
    ],
) -> VacancyRankingDTO:
    return await use_case.execute(vacancy_id)
