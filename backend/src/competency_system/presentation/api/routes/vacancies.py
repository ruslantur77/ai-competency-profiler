from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancyListItemDTO,
    VacancyStatusUpdateDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.use_cases.vacancy import (
    DecideVacancySuggestionUseCase,
    ExtractVacancyGraphUseCase,
    FinalizeVacancyGraphUseCase,
    GetVacancyGraphUseCase,
    ListVacanciesForReviewUseCase,
    ListVacanciesUseCase,
    ListVacancySuggestionsUseCase,
    UpdateVacancyStatusUseCase,
)
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.presentation.api.dependencies import (
    get_decide_vacancy_suggestion_use_case,
    get_extract_vacancy_graph_use_case,
    get_finalize_vacancy_graph_use_case,
    get_get_vacancy_graph_use_case,
    get_list_vacancies_for_review_use_case,
    get_list_vacancies_use_case,
    get_list_vacancy_suggestions_use_case,
    get_update_vacancy_status_use_case,
    require_admin_or_expert,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@router.get("", response_model=list[VacancyListItemDTO])
async def list_vacancies(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[ListVacanciesUseCase, Depends(get_list_vacancies_use_case)],
    status_filter: VacancyStatus,
) -> list[VacancyListItemDTO]:
    return await use_case.execute(statuses={status_filter})


@router.get("/review-queue", response_model=list[VacancyListItemDTO])
async def list_vacancies_for_review(
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        ListVacanciesForReviewUseCase,
        Depends(get_list_vacancies_for_review_use_case),
    ],
) -> list[VacancyListItemDTO]:
    return await use_case.execute()


@router.post("", response_model=VacancyDTO, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    payload: VacancyCreateDTO,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ExtractVacancyGraphUseCase,
        Depends(get_extract_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    try:
        return await use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/{vacancy_id}", response_model=VacancyDTO)
async def get_vacancy(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyGraphUseCase,
        Depends(get_get_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    try:
        return await use_case.execute(vacancy_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{vacancy_id}/graph", response_model=VacancyDTO)
async def get_vacancy_graph(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyGraphUseCase,
        Depends(get_get_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    try:
        return await use_case.execute(vacancy_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/{vacancy_id}/graph", response_model=VacancyDTO)
async def finalize_vacancy_graph(
    vacancy_id: UUID,
    payload: VacancyGraphUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        FinalizeVacancyGraphUseCase,
        Depends(get_finalize_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    try:
        return await use_case.execute(vacancy_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/{vacancy_id}/status", response_model=VacancyDTO)
async def update_vacancy_status(
    vacancy_id: UUID,
    payload: VacancyStatusUpdateDTO,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        UpdateVacancyStatusUseCase,
        Depends(get_update_vacancy_status_use_case),
    ],
) -> VacancyDTO:
    try:
        return await use_case.execute(vacancy_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{vacancy_id}/suggestions", response_model=list[VacancyGraphSuggestionDTO])
async def list_vacancy_suggestions(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ListVacancySuggestionsUseCase,
        Depends(get_list_vacancy_suggestions_use_case),
    ],
) -> list[VacancyGraphSuggestionDTO]:
    return await use_case.execute(vacancy_id)


@router.post(
    "/{vacancy_id}/suggestions/decision", response_model=VacancyGraphSuggestionDTO
)
async def decide_vacancy_suggestion(
    vacancy_id: UUID,
    payload: VacancySuggestionDecisionDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        DecideVacancySuggestionUseCase,
        Depends(get_decide_vacancy_suggestion_use_case),
    ],
) -> VacancyGraphSuggestionDTO:
    try:
        return await use_case.execute(vacancy_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
