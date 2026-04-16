from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams

from competency_system.application.dtos.candidate import CandidateListItemDto
from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancyListItemDTO,
    VacancyStatusUpdateDTO,
    VacancySuggestionBulkDecisionDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.use_cases.candidate import (
    ListVacancyCandidatesUseCase,
)
from competency_system.application.use_cases.vacancy import (
    CreateVacancyGraphUseCase,
    DecideVacancySuggestionsUseCase,
    DecideVacancySuggestionUseCase,
    FinalizeVacancyGraphUseCase,
    GetVacancyGraphUseCase,
    ListVacanciesForReviewUseCase,
    ListVacanciesUseCase,
    ListVacancySuggestionsUseCase,
    SaveVacancyGraphUseCase,
    UpdateVacancyStatusUseCase,
)
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.presentation.api.dependencies import (
    get_decide_vacancy_suggestion_use_case,
    get_decide_vacancy_suggestions_use_case,
    get_extract_vacancy_graph_use_case,
    get_finalize_vacancy_graph_use_case,
    get_get_vacancy_graph_use_case,
    get_list_vacancies_for_review_use_case,
    get_list_vacancies_use_case,
    get_list_vacancy_candidates_use_case,
    get_list_vacancy_suggestions_use_case,
    get_save_vacancy_graph_use_case,
    get_update_vacancy_status_use_case,
    require_admin_or_expert,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@router.get("", response_model=LimitOffsetPage[VacancyListItemDTO])
async def list_vacancies(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[ListVacanciesUseCase, Depends(get_list_vacancies_use_case)],
    params: Annotated[LimitOffsetParams, Depends()],
    status_filter: Annotated[list[VacancyStatus] | None, Query()] = None,
) -> LimitOffsetPage[VacancyListItemDTO]:
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


@router.get("/review-queue", response_model=LimitOffsetPage[VacancyListItemDTO])
async def list_vacancies_for_review(
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        ListVacanciesForReviewUseCase,
        Depends(get_list_vacancies_for_review_use_case),
    ],
    params: Annotated[LimitOffsetParams, Depends()],
) -> LimitOffsetPage[VacancyListItemDTO]:
    result = await use_case.execute(limit=params.limit, offset=params.offset)
    return LimitOffsetPage.create(
        items=result.items,
        total=result.total,
        params=params,
    )


@router.post("", response_model=VacancyDTO, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    payload: VacancyCreateDTO,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        CreateVacancyGraphUseCase,
        Depends(get_extract_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    return await use_case.execute(payload)


@router.get("/{vacancy_id}", response_model=VacancyDTO)
async def get_vacancy(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyGraphUseCase,
        Depends(get_get_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    return await use_case.execute(vacancy_id)


@router.get("/{vacancy_id}/graph", response_model=VacancyDTO)
async def get_vacancy_graph(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetVacancyGraphUseCase,
        Depends(get_get_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    return await use_case.execute(vacancy_id)


@router.patch("/{vacancy_id}/graph", response_model=VacancyDTO)
async def save_vacancy_graph(
    vacancy_id: UUID,
    payload: VacancyGraphUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        SaveVacancyGraphUseCase,
        Depends(get_save_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    return await use_case.execute(vacancy_id, payload)


@router.post("/{vacancy_id}/graph/finalize", response_model=VacancyDTO)
async def finalize_vacancy_graph(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        FinalizeVacancyGraphUseCase,
        Depends(get_finalize_vacancy_graph_use_case),
    ],
) -> VacancyDTO:
    return await use_case.execute(vacancy_id)


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
    return await use_case.execute(vacancy_id, payload)


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
    return await use_case.execute(vacancy_id, payload)


@router.post(
    "/{vacancy_id}/suggestions/decisions",
    response_model=list[VacancyGraphSuggestionDTO],
)
async def decide_vacancy_suggestions(
    vacancy_id: UUID,
    payload: VacancySuggestionBulkDecisionDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        DecideVacancySuggestionsUseCase,
        Depends(get_decide_vacancy_suggestions_use_case),
    ],
) -> list[VacancyGraphSuggestionDTO]:
    return await use_case.execute(vacancy_id, payload)


@router.get("/{vacancy_id}/candidates", response_model=list[CandidateListItemDto])
async def list_vacancy_candidates(
    vacancy_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ListVacancyCandidatesUseCase,
        Depends(get_list_vacancy_candidates_use_case),
    ],
) -> list[CandidateListItemDto]:
    return await use_case.execute(vacancy_id)
