from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from competency_system.application.dtos.competency import (
    CategoryDTO,
    CompetencyDTO,
    SubCompetencyDTO,
)
from competency_system.application.dtos.vacancy import (
    VacancyCategoryExtractionResultDTO,
    VacancyCategorySuggestionDTO,
    VacancyCompetencyExtractionResultDTO,
    VacancyCompetencySuggestionDTO,
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancySubCompetencyExtractionResultDTO,
    VacancySubCompetencySuggestionDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.uow import UnitOfWork
from competency_system.application.use_cases.llm_orchestrator import (
    LLMCallSpec,
    StructuredLLMOrchestrator,
    normalize_weighted_items,
)
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
    VacancyGraphSuggestion,
)
from competency_system.domain.value_objects.enums import (
    SuggestionEntityType,
    SuggestionStage,
    SuggestionStatus,
    VacancyStatus,
)


@dataclass(frozen=True)
class _VacancyGraphPayload:
    categories: list[Category]
    competencies: list[Competency]
    suggestions: list[VacancyGraphSuggestion]


@dataclass(frozen=True)
class _CatalogItem:
    id: UUID
    name: str
    description: str


class _IdMapper:
    def __init__(self, items: list[_CatalogItem]) -> None:
        self._int_to_uuid = {index: item.id for index, item in enumerate(items, start=1)}
        self._uuid_to_int = {item.id: index for index, item in enumerate(items, start=1)}
        self._uuid_to_item = {item.id: item for item in items}
        self._items = items

    def to_prompt_items(self) -> list[dict[str, object]]:
        return [
            {
                "llm_id": index,
                "name": item.name,
                "description": item.description,
            }
            for index, item in enumerate(self._items, start=1)
        ]

    def resolve_uuid(
        self,
        *,
        llm_id: int | None,
        direct_id: UUID | None,
    ) -> UUID | None:
        if direct_id is not None:
            return direct_id
        if llm_id is None:
            return None
        return self._int_to_uuid.get(llm_id)

    def get_item(self, item_id: UUID) -> _CatalogItem | None:
        return self._uuid_to_item.get(item_id)


def _vacancy_to_dto(vacancy: Vacancy) -> VacancyDTO:
    return VacancyDTO(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        experience=vacancy.experience,
        key_skills=vacancy.key_skills,
        categories=[_category_to_dto(category) for category in vacancy.categories],
        competencies=[_competency_to_dto(competency) for competency in vacancy.competencies],
        error_message=vacancy.error_message,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def _suggestion_to_dto(suggestion: VacancyGraphSuggestion) -> VacancyGraphSuggestionDTO:
    return VacancyGraphSuggestionDTO(
        id=suggestion.id,
        vacancy_id=suggestion.vacancy_id,
        stage=suggestion.stage,
        entity_type=suggestion.entity_type,
        status=suggestion.status,
        name=suggestion.name,
        description=suggestion.description,
        reason=suggestion.reason,
        parent_category_id=suggestion.parent_category_id,
        parent_competency_id=suggestion.parent_competency_id,
        is_required=suggestion.is_required,
        target_level=suggestion.target_level,
        weight=suggestion.weight,
    )


def _category_to_dto(category: Category) -> CategoryDTO:
    return CategoryDTO(
        id=category.id,
        name=category.name,
        description=category.description,
        emoji=category.emoji,
        competencies=[_competency_to_dto(competency) for competency in category.competencies],
    )


def _competency_to_dto(competency: Competency) -> CompetencyDTO:
    return CompetencyDTO(
        id=competency.id,
        category_id=competency.category_id,
        name=competency.name,
        description=competency.description,
        is_required=competency.is_required,
        sub_competencies=[
            _subcompetency_to_dto(subcompetency) for subcompetency in competency.sub_competencies
        ],
    )


def _subcompetency_to_dto(subcompetency: SubCompetency) -> SubCompetencyDTO:
    return SubCompetencyDTO(
        id=subcompetency.id,
        name=subcompetency.name,
        description=subcompetency.description,
        target_level=subcompetency.target_level,
        weight=subcompetency.weight,
    )


class ExtractVacancyGraphUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: LLMGateway,
        *,
        max_categories: int = 6,
        max_competencies: int = 10,
        max_subcompetencies: int = 6,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
    ) -> None:
        self._uow = uow
        self._llm_orchestrator = StructuredLLMOrchestrator(
            llm_gateway,
            max_parallel_requests=max_parallel_requests,
            stage_timeout_seconds=stage_timeout_seconds,
        )
        self._max_categories = max_categories
        self._max_competencies = max_competencies
        self._max_subcompetencies = max_subcompetencies

    async def execute(self, command: VacancyCreateDTO) -> VacancyDTO:
        vacancy = Vacancy(
            name=command.name,
            description=command.description,
            experience=command.experience,
            key_skills=list(command.key_skills),
            status=VacancyStatus.EXTRACTING,
        )

        try:
            async with self._uow as uow:
                existing_categories = list(await uow.categories.list())
                graph = await self._build_graph(vacancy, existing_categories)

                vacancy.status = VacancyStatus.DRAFT
                vacancy.categories = graph.categories
                vacancy.competencies = graph.competencies

                for category in vacancy.categories:
                    await uow.categories.add(category)
                await uow.vacancies.add(vacancy)
                for suggestion in graph.suggestions:
                    suggestion.vacancy_id = vacancy.id
                    await uow.vacancy_suggestions.add(suggestion)
                await uow.commit()
                return _vacancy_to_dto(vacancy)
        except Exception as exc:
            vacancy.status = VacancyStatus.FAILED
            vacancy.error_message = str(exc)
            async with self._uow as uow:
                await uow.vacancies.add(vacancy)
                await uow.commit()
            raise

    async def _build_graph(
        self,
        vacancy: Vacancy,
        existing_categories: list[Category],
    ) -> _VacancyGraphPayload:
        category_catalog = [
            _CatalogItem(id=category.id, name=category.name, description=category.description)
            for category in existing_categories
        ]
        category_mapper = _IdMapper(category_catalog)
        category_result = await self._llm_orchestrator.run(
            LLMCallSpec(
                stage="vacancy_categories",
                messages=self._build_category_messages(vacancy, category_mapper),
                response_model=VacancyCategoryExtractionResultDTO,
                temperature=0.1,
            )
        )
        categories = self._materialize_categories(
            category_result.categories[: self._max_categories],
            category_mapper,
        )

        extracted = await self._extract_competencies_parallel(
            vacancy,
            categories,
            existing_categories,
        )
        all_competencies = [comp for _, competencies, _ in extracted for comp in competencies]
        all_suggestions = list(category_result.suggested_new)
        suggestions: list[VacancyGraphSuggestion] = [
            self._category_suggestion_to_entity(vacancy.id, item)
            for item in all_suggestions
        ]
        for category, competencies, category_suggestions in extracted:
            category.competencies = competencies
            suggestions.extend(category_suggestions)
        return _VacancyGraphPayload(
            categories=categories,
            competencies=all_competencies,
            suggestions=suggestions,
        )

    async def _extract_competencies_parallel(
        self,
        vacancy: Vacancy,
        categories: list[Category],
        catalog_categories: list[Category],
    ) -> list[tuple[Category, list[Competency], list[VacancyGraphSuggestion]]]:
        catalog_by_id = {item.id: item for item in catalog_categories}
        specs: list[LLMCallSpec[VacancyCompetencyExtractionResultDTO]] = []
        context: list[tuple[Category, _IdMapper]] = []
        for category in categories:
            existing_competencies = (
                list(catalog_by_id[category.id].competencies)
                if category.id in catalog_by_id
                else []
            )
            competency_mapper = _IdMapper(
                [
                    _CatalogItem(
                        id=competency.id,
                        name=competency.name,
                        description=competency.description,
                    )
                    for competency in existing_competencies
                ]
            )
            context.append((category, competency_mapper))
            specs.append(
                LLMCallSpec(
                    stage="vacancy_competencies",
                    messages=self._build_competency_messages(
                        vacancy,
                        category,
                        competency_mapper,
                    ),
                    response_model=VacancyCompetencyExtractionResultDTO,
                    temperature=0.1,
                )
            )
        responses = await self._llm_orchestrator.run_many(specs)
        output: list[tuple[Category, list[Competency], list[VacancyGraphSuggestion]]] = []
        for (category, mapper), response in zip(context, responses, strict=False):
            competencies = self._materialize_competencies(
                response.competencies[: self._max_competencies],
                category.id,
                mapper,
            )
            sub_suggestions: list[VacancyGraphSuggestion] = []
            suggestions = [
                self._competency_suggestion_to_entity(vacancy.id, category.id, item)
                for item in response.suggested_new
            ]
            await self._fill_subcompetencies_parallel(
                vacancy,
                category,
                competencies,
                mapper,
                existing_competencies,
                sub_suggestions,
            )
            output.append((category, competencies, suggestions + sub_suggestions))
        return output

    async def _fill_subcompetencies_parallel(
        self,
        vacancy: Vacancy,
        category: Category,
        competencies: list[Competency],
        competency_mapper: _IdMapper,
        existing_competencies: list[Competency],
        sub_suggestions: list[VacancyGraphSuggestion],
    ) -> None:
        existing_competency_by_id = {item.id: item for item in existing_competencies}
        specs: list[LLMCallSpec[VacancySubCompetencyExtractionResultDTO]] = []
        context: list[tuple[Competency, _IdMapper]] = []
        for competency in competencies:
            catalog_subs: list[_CatalogItem] = []
            existing_comp = existing_competency_by_id.get(competency.id)
            if existing_comp is not None:
                catalog_subs = [
                    _CatalogItem(
                        id=sub.id,
                        name=sub.name,
                        description=sub.description,
                    )
                    for sub in existing_comp.sub_competencies
                ]
            sub_mapper = _IdMapper(catalog_subs)
            context.append((competency, sub_mapper))
            specs.append(
                LLMCallSpec(
                    stage="vacancy_subcompetencies",
                    messages=self._build_subcompetency_messages(
                        vacancy,
                        category,
                        competency,
                        sub_mapper,
                    ),
                    response_model=VacancySubCompetencyExtractionResultDTO,
                    temperature=0.1,
                )
            )
        responses = await self._llm_orchestrator.run_many(specs)
        for (competency, sub_mapper), response in zip(context, responses, strict=False):
            subs = self._materialize_subcompetencies(
                response.sub_competencies[: self._max_subcompetencies],
                sub_mapper,
            )
            competency.sub_competencies = subs
            sub_suggestions.extend(
                self._subcompetency_suggestion_to_entity(
                    vacancy.id,
                    category.id,
                    competency.id,
                    suggestion_item,
                )
                for suggestion_item in response.suggested_new
            )

    def _build_category_messages(
        self,
        vacancy: Vacancy,
        category_mapper: _IdMapper,
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=(
                    "You extract competency categories for an IT vacancy.\n"
                    "Return JSON only with keys: categories, suggested_new.\n"
                    "For existing categories always return llm_id.\n"
                    "For new categories omit llm_id and provide name/description/emoji/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
                            "experience": vacancy.experience,
                            "key_skills": vacancy.key_skills,
                        },
                        "existing_categories": category_mapper.to_prompt_items(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _build_competency_messages(
        self,
        vacancy: Vacancy,
        category: Category,
        competency_mapper: _IdMapper,
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=(
                    "You extract competencies inside one category for an IT vacancy.\n"
                    "Return JSON only with keys: competencies, suggested_new.\n"
                    "For existing competencies always return llm_id.\n"
                    "For new competencies omit llm_id and provide name/description/is_required/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
                            "experience": vacancy.experience,
                            "key_skills": vacancy.key_skills,
                        },
                        "category": {
                            "id": str(category.id),
                            "name": category.name,
                            "description": category.description,
                            "emoji": category.emoji,
                        },
                        "existing_competencies": competency_mapper.to_prompt_items(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _build_subcompetency_messages(
        self,
        vacancy: Vacancy,
        category: Category,
        competency: Competency,
        sub_mapper: _IdMapper,
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=(
                    "You extract subcompetencies inside one competency for an IT vacancy.\n"
                    "Return JSON only with keys: sub_competencies, suggested_new.\n"
                    "For existing subcompetencies always return llm_id.\n"
                    "For new subcompetencies omit llm_id and provide name/description/target_level/weight/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
                            "experience": vacancy.experience,
                            "key_skills": vacancy.key_skills,
                        },
                        "category": {
                            "id": str(category.id),
                            "name": category.name,
                            "description": category.description,
                            "emoji": category.emoji,
                        },
                        "competency": {
                            "id": str(competency.id),
                            "name": competency.name,
                            "description": competency.description,
                        },
                        "existing_subcompetencies": sub_mapper.to_prompt_items(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _materialize_categories(
        self,
        suggestions: list[VacancyCategorySuggestionDTO],
        mapper: _IdMapper,
    ) -> list[Category]:
        categories: list[Category] = []
        for suggestion in suggestions:
            category_id = mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id) or uuid4()
            catalog_item = mapper.get_item(category_id)
            categories.append(
                Category(
                    id=category_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description or (catalog_item.description if catalog_item else ""),
                    emoji=suggestion.emoji,
                )
            )
        return categories

    def _materialize_competencies(
        self,
        suggestions: list[VacancyCompetencySuggestionDTO],
        category_id: UUID,
        mapper: _IdMapper,
    ) -> list[Competency]:
        suggestions = normalize_weighted_items(suggestions)
        competencies: list[Competency] = []
        for suggestion in suggestions:
            competency_id = mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id) or uuid4()
            catalog_item = mapper.get_item(competency_id)
            competencies.append(
                Competency(
                    id=competency_id,
                    category_id=suggestion.category_id or category_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description or (catalog_item.description if catalog_item else ""),
                    is_required=suggestion.is_required,
                )
            )
        return competencies

    def _materialize_subcompetencies(
        self,
        suggestions: list[VacancySubCompetencySuggestionDTO],
        mapper: _IdMapper,
    ) -> list[SubCompetency]:
        if not suggestions:
            return []
        suggestions = normalize_weighted_items(suggestions)
        subcompetencies: list[SubCompetency] = []
        for suggestion in suggestions:
            sub_id = mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id) or uuid4()
            catalog_item = mapper.get_item(sub_id)
            subcompetencies.append(
                SubCompetency(
                    id=sub_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description or (catalog_item.description if catalog_item else ""),
                    target_level=suggestion.target_level,
                    weight=suggestion.weight,
                )
            )
        return subcompetencies

    def _category_suggestion_to_entity(
        self,
        vacancy_id: UUID,
        suggestion: VacancyCategorySuggestionDTO,
    ) -> VacancyGraphSuggestion:
        return VacancyGraphSuggestion(
            id=uuid4(),
            vacancy_id=vacancy_id,
            stage=SuggestionStage.CATEGORY,
            entity_type=SuggestionEntityType.CATEGORY,
            status=SuggestionStatus.PENDING,
            name=suggestion.name,
            description=suggestion.description,
            reason=suggestion.reason,
        )

    def _competency_suggestion_to_entity(
        self,
        vacancy_id: UUID,
        category_id: UUID,
        suggestion: VacancyCompetencySuggestionDTO,
    ) -> VacancyGraphSuggestion:
        return VacancyGraphSuggestion(
            id=uuid4(),
            vacancy_id=vacancy_id,
            stage=SuggestionStage.COMPETENCY,
            entity_type=SuggestionEntityType.COMPETENCY,
            status=SuggestionStatus.PENDING,
            name=suggestion.name,
            description=suggestion.description,
            reason=suggestion.reason,
            parent_category_id=category_id,
            is_required=suggestion.is_required,
            weight=suggestion.weight,
            target_level=suggestion.required_level,
        )

    def _subcompetency_suggestion_to_entity(
        self,
        vacancy_id: UUID,
        category_id: UUID,
        competency_id: UUID,
        suggestion: VacancySubCompetencySuggestionDTO,
    ) -> VacancyGraphSuggestion:
        return VacancyGraphSuggestion(
            id=uuid4(),
            vacancy_id=vacancy_id,
            stage=SuggestionStage.SUB_COMPETENCY,
            entity_type=SuggestionEntityType.SUB_COMPETENCY,
            status=SuggestionStatus.PENDING,
            name=suggestion.name,
            description=suggestion.description,
            reason=suggestion.reason,
            parent_category_id=category_id,
            parent_competency_id=competency_id,
            target_level=suggestion.target_level,
            weight=suggestion.weight,
        )


class FinalizeVacancyGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        vacancy_id: UUID,
        graph: VacancyGraphUpdateDTO,
    ) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")

            payload = self._build_payload(graph)
            vacancy.status = VacancyStatus.READY
            vacancy.categories = payload.categories
            vacancy.competencies = payload.competencies
            vacancy.error_message = graph.error_message

            for decision in graph.suggestion_decisions:
                suggestion = await uow.vacancy_suggestions.get(decision.suggestion_id)
                if suggestion is None or suggestion.vacancy_id != vacancy_id:
                    continue
                suggestion.status = decision.status
                await uow.vacancy_suggestions.add(suggestion)

            for category in vacancy.categories:
                await uow.categories.add(category)
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return _vacancy_to_dto(vacancy)

    def _build_payload(self, graph: VacancyGraphUpdateDTO) -> _VacancyGraphPayload:
        categories: list[Category] = []
        competencies: list[Competency] = []

        for category_dto in graph.categories:
            category = Category(
                id=category_dto.id,
                name=category_dto.name,
                description=category_dto.description,
                emoji=category_dto.emoji,
            )
            category_competencies: list[Competency] = []
            for competency_dto in category_dto.competencies:
                competency = Competency(
                    id=competency_dto.id,
                    category_id=category.id,
                    name=competency_dto.name,
                    description=competency_dto.description,
                    is_required=competency_dto.is_required,
                    sub_competencies=[
                        SubCompetency(
                            id=subcompetency_dto.id,
                            name=subcompetency_dto.name,
                            description=subcompetency_dto.description,
                            target_level=subcompetency_dto.target_level,
                            weight=subcompetency_dto.weight,
                        )
                        for subcompetency_dto in competency_dto.sub_competencies
                    ],
                )
                category_competencies.append(competency)
                competencies.append(competency)

            category.competencies = category_competencies
            categories.append(category)

        return _VacancyGraphPayload(
            categories=categories,
            competencies=competencies,
            suggestions=[],
        )


class GetVacancyGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")
            return _vacancy_to_dto(vacancy)


class ListVacancySuggestionsUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> list[VacancyGraphSuggestionDTO]:
        async with self._uow as uow:
            suggestions = await uow.vacancy_suggestions.list_by_vacancy(vacancy_id)
            return [_suggestion_to_dto(suggestion) for suggestion in suggestions]


class DecideVacancySuggestionUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID, decision: VacancySuggestionDecisionDTO) -> VacancyGraphSuggestionDTO:
        if decision.status == SuggestionStatus.PENDING:
            raise ValueError("Decision status must be approved or rejected")
        async with self._uow as uow:
            suggestion = await uow.vacancy_suggestions.get(decision.suggestion_id)
            if suggestion is None or suggestion.vacancy_id != vacancy_id:
                raise ValueError(f"Suggestion {decision.suggestion_id} not found")
            suggestion.status = decision.status
            await uow.vacancy_suggestions.add(suggestion)
            await uow.commit()
            return _suggestion_to_dto(suggestion)
