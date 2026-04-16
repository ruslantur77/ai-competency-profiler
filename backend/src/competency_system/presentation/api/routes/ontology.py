from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from competency_system.application.dtos.competency import (
    CategoryCreateDTO,
    CategoryDTO,
    CategoryUpdateDTO,
    CompetencyCreateDTO,
    CompetencyDTO,
    CompetencyUpdateDTO,
    SubCompetencyCreateDTO,
    SubCompetencyDTO,
    SubCompetencyUpdateDTO,
)
from competency_system.application.use_cases.ontology import (
    CreateCategoryUseCase,
    CreateCompetencyUseCase,
    CreateSubCompetencyUseCase,
    GetCategoryUseCase,
    GetCompetencyUseCase,
    GetSubCompetencyUseCase,
    ListCategoriesUseCase,
    ListCompetenciesUseCase,
    ListSubCompetenciesUseCase,
    UpdateCategoryUseCase,
    UpdateCompetencyUseCase,
    UpdateSubCompetencyUseCase,
)
from competency_system.presentation.api.dependencies import (
    get_create_category_use_case,
    get_create_competency_use_case,
    get_create_sub_competency_use_case,
    get_get_category_use_case,
    get_get_competency_use_case,
    get_get_sub_competency_use_case,
    get_list_categories_use_case,
    get_list_competencies_use_case,
    get_list_sub_competencies_use_case,
    get_update_category_use_case,
    get_update_competency_use_case,
    get_update_sub_competency_use_case,
    require_admin_or_expert,
    require_hr_expert_admin,
)

router = APIRouter(prefix="/ontology", tags=["ontology"])


@router.get("/categories", response_model=list[CategoryDTO])
async def list_categories(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ListCategoriesUseCase,
        Depends(get_list_categories_use_case),
    ],
) -> list[CategoryDTO]:
    return await use_case.execute()


@router.get("/categories/{category_id}", response_model=CategoryDTO)
async def get_category(
    category_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[GetCategoryUseCase, Depends(get_get_category_use_case)],
) -> CategoryDTO:
    try:
        return await use_case.execute(category_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/categories", response_model=CategoryDTO, status_code=status.HTTP_201_CREATED
)
async def create_category(
    payload: CategoryCreateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        CreateCategoryUseCase,
        Depends(get_create_category_use_case),
    ],
) -> CategoryDTO:
    return await use_case.execute(payload)


@router.patch("/categories/{category_id}", response_model=CategoryDTO)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        UpdateCategoryUseCase,
        Depends(get_update_category_use_case),
    ],
) -> CategoryDTO:
    try:
        return await use_case.execute(category_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/competencies", response_model=list[CompetencyDTO])
async def list_competencies(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ListCompetenciesUseCase,
        Depends(get_list_competencies_use_case),
    ],
) -> list[CompetencyDTO]:
    return await use_case.execute()


@router.get("/competencies/{competency_id}", response_model=CompetencyDTO)
async def get_competency(
    competency_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetCompetencyUseCase,
        Depends(get_get_competency_use_case),
    ],
) -> CompetencyDTO:
    try:
        return await use_case.execute(competency_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/competencies",
    response_model=CompetencyDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_competency(
    payload: CompetencyCreateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        CreateCompetencyUseCase,
        Depends(get_create_competency_use_case),
    ],
) -> CompetencyDTO:
    try:
        return await use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/competencies/{competency_id}", response_model=CompetencyDTO)
async def update_competency(
    competency_id: UUID,
    payload: CompetencyUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        UpdateCompetencyUseCase,
        Depends(get_update_competency_use_case),
    ],
) -> CompetencyDTO:
    try:
        return await use_case.execute(competency_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message and message.startswith("Competency")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/sub-competencies", response_model=list[SubCompetencyDTO])
async def list_sub_competencies(
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        ListSubCompetenciesUseCase,
        Depends(get_list_sub_competencies_use_case),
    ],
) -> list[SubCompetencyDTO]:
    return await use_case.execute()


@router.get("/sub-competencies/{sub_competency_id}", response_model=SubCompetencyDTO)
async def get_sub_competency(
    sub_competency_id: UUID,
    _: Annotated[None, Depends(require_hr_expert_admin)],
    use_case: Annotated[
        GetSubCompetencyUseCase,
        Depends(get_get_sub_competency_use_case),
    ],
) -> SubCompetencyDTO:
    try:
        return await use_case.execute(sub_competency_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/sub-competencies",
    response_model=SubCompetencyDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_sub_competency(
    payload: SubCompetencyCreateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        CreateSubCompetencyUseCase,
        Depends(get_create_sub_competency_use_case),
    ],
) -> SubCompetencyDTO:
    try:
        return await use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/sub-competencies/{sub_competency_id}",
    response_model=SubCompetencyDTO,
)
async def update_sub_competency(
    sub_competency_id: UUID,
    payload: SubCompetencyUpdateDTO,
    _: Annotated[None, Depends(require_admin_or_expert)],
    use_case: Annotated[
        UpdateSubCompetencyUseCase,
        Depends(get_update_sub_competency_use_case),
    ],
) -> SubCompetencyDTO:
    try:
        return await use_case.execute(sub_competency_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message and message.startswith("Sub-competency")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
