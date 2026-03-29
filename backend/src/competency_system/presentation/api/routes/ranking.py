from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.ranking import VacancyRankingDTO
from competency_system.application.use_cases.ranking import (
    GetVacancyRankingUseCase,
    RecalculateRankingUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_get_vacancy_ranking_use_case,
    get_recalculate_ranking_use_case,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/vacancies", tags=["ranking"])


async def _recalculate_ranking(
    vacancy_id: UUID,
    use_case: RecalculateRankingUseCase | GetVacancyRankingUseCase,
) -> VacancyRankingDTO:
    try:
        return await use_case.execute(vacancy_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{vacancy_id}/rankings", response_model=VacancyRankingDTO)
async def get_vacancy_rankings(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyRankingUseCase, Depends(get_get_vacancy_ranking_use_case)
    ],
) -> VacancyRankingDTO:
    return await _recalculate_ranking(vacancy_id, use_case)


@router.get(
    "/{vacancy_id}/ranking", response_model=VacancyRankingDTO, include_in_schema=False
)
async def recalculate_ranking(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        RecalculateRankingUseCase, Depends(get_recalculate_ranking_use_case)
    ],
) -> VacancyRankingDTO:
    return await _recalculate_ranking(vacancy_id, use_case)


@router.get(
    "/{vacancy_id}/candidates",
    response_model=VacancyRankingDTO,
    include_in_schema=False,
)
async def get_vacancy_candidates(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        RecalculateRankingUseCase, Depends(get_recalculate_ranking_use_case)
    ],
) -> VacancyRankingDTO:
    return await _recalculate_ranking(vacancy_id, use_case)
