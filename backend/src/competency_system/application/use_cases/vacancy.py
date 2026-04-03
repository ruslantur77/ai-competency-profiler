from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from competency_system.application.dtos.vacancy import (
    VacancyCategoryExtractionResultDTO,
    VacancyCategoryNodeDTO,
    VacancyCategorySuggestionDTO,
    VacancyCompetencyExtractionResultDTO,
    VacancyCompetencyNodeDTO,
    VacancyCompetencySuggestionDTO,
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancyListItemDTO,
    VacancyStatusUpdateDTO,
    VacancySubCompetencyExtractionResultDTO,
    VacancySubCompetencyNodeDTO,
    VacancySubCompetencySuggestionDTO,
    VacancySuggestionDecisionDTO,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.llm_jobs import LLMJobQueuePort, LLMJobType
from competency_system.application.ports.repositories import (
    CategoryInclude,
    VacancyInclude,
)
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
    VacancyCategoryNode,
    VacancyCompetencyNode,
    VacancyGraphSuggestion,
    VacancySubCompetencyNode,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
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
    category_nodes: list[VacancyCategoryNode]
    competency_nodes: list[VacancyCompetencyNode]
    sub_competency_nodes: list[VacancySubCompetencyNode]
    suggestions: list[VacancyGraphSuggestion]


@dataclass(frozen=True)
class _CatalogItem:
    id: UUID
    name: str
    description: str


class _IdMapper:
    def __init__(self, items: list[_CatalogItem]) -> None:
        self._int_to_uuid = {
            index: item.id for index, item in enumerate(items, start=1)
        }
        self._uuid_to_int = {
            item.id: index for index, item in enumerate(items, start=1)
        }
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
        category_nodes=[
            VacancyCategoryNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                category_id=node.category_id,
                position=node.position,
                category_name=node.category.name if node.category else "",
                category_description=node.category.description if node.category else "",
                category_emoji=node.category.emoji if node.category else "",
            )
            for node in vacancy.category_nodes
        ],
        competency_nodes=[
            VacancyCompetencyNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                competency_id=node.competency_id,
                category_id=node.category_id,
                is_required=node.is_required,
                position=node.position,
                competency_name=node.competency.name if node.competency else "",
                competency_description=(
                    node.competency.description if node.competency else ""
                ),
            )
            for node in vacancy.competency_nodes
        ],
        sub_competency_nodes=[
            VacancySubCompetencyNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                sub_competency_id=node.sub_competency_id,
                competency_id=node.competency_id,
                target_level=node.target_level,
                weight=node.weight,
                position=node.position,
                sub_competency_name=(
                    node.sub_competency.name if node.sub_competency else ""
                ),
                sub_competency_description=(
                    node.sub_competency.description if node.sub_competency else ""
                ),
            )
            for node in vacancy.sub_competency_nodes
        ],
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


def _vacancy_to_list_item(vacancy: Vacancy) -> VacancyListItemDTO:
    return VacancyListItemDTO(
        id=vacancy.id,
        name=vacancy.name,
        status=vacancy.status,
        created_at=vacancy.created_at,
    )


def _build_nodes_from_competencies(
    vacancy_id: UUID,
    competencies: list[Competency],
) -> tuple[
    list[VacancyCategoryNode],
    list[VacancyCompetencyNode],
    list[VacancySubCompetencyNode],
]:
    category_order: list[UUID] = []
    seen_categories: set[UUID] = set()
    for competency in competencies:
        if competency.category_id in seen_categories:
            continue
        seen_categories.add(competency.category_id)
        category_order.append(competency.category_id)

    category_nodes = [
        VacancyCategoryNode(
            id=uuid4(),
            vacancy_id=vacancy_id,
            category_id=category_id,
            position=position,
        )
        for position, category_id in enumerate(category_order)
    ]

    competency_nodes: list[VacancyCompetencyNode] = []
    sub_nodes: list[VacancySubCompetencyNode] = []
    for position, competency in enumerate(competencies):
        competency_nodes.append(
            VacancyCompetencyNode(
                id=uuid4(),
                vacancy_id=vacancy_id,
                competency_id=competency.id,
                category_id=competency.category_id,
                is_required=True,
                position=position,
            )
        )
        for sub in competency.sub_competencies:
            sub_nodes.append(
                VacancySubCompetencyNode(
                    id=uuid4(),
                    vacancy_id=vacancy_id,
                    sub_competency_id=sub.id,
                    competency_id=competency.id,
                    target_level=CompetencyLevel.BEGINNER,
                    weight=sub.weight,
                    position=len(sub_nodes),
                )
            )
    return category_nodes, competency_nodes, sub_nodes


class ExtractVacancyGraphUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: LLMGateway,
        job_queue: LLMJobQueuePort,
        *,
        max_categories: int = 6,
        max_competencies: int = 10,
        max_subcompetencies: int = 6,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
    ) -> None:
        self._uow = uow
        self._job_queue = job_queue
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
            status=VacancyStatus.EXTRACTING,
        )
        async with self._uow as uow:
            await uow.vacancies.add(vacancy)
            await uow.commit()
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.VACANCY_EXTRACTION,
            payload={"vacancy_id": str(vacancy.id)},
            runner=lambda: self._process_extraction(vacancy.id),
        )
        return _vacancy_to_dto(vacancy)

    async def _process_extraction(self, vacancy_id: UUID) -> None:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                return
            try:
                existing_categories = list(
                    await uow.categories.get_list(
                        include={CategoryInclude.SUB_COMPETENCIES}
                    )
                )
                graph = await self._build_graph(vacancy, existing_categories)
                vacancy.status = VacancyStatus.DRAFT
                vacancy.category_nodes = graph.category_nodes
                vacancy.competency_nodes = graph.competency_nodes
                vacancy.sub_competency_nodes = graph.sub_competency_nodes
                vacancy.error_message = None

                for category in graph.categories:
                    await uow.categories.add(category)
                await uow.vacancies.add(vacancy)
                for suggestion in graph.suggestions:
                    suggestion.vacancy_id = vacancy.id
                    await uow.vacancy_suggestions.add(suggestion)
            except Exception as exc:
                vacancy.status = VacancyStatus.FAILED
                vacancy.error_message = str(exc)
                await uow.vacancies.add(vacancy)
            await uow.commit()

    async def _build_graph(
        self,
        vacancy: Vacancy,
        existing_categories: list[Category],
    ) -> _VacancyGraphPayload:
        category_catalog = [
            _CatalogItem(
                id=category.id, name=category.name, description=category.description
            )
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
        all_competencies = [
            comp for _, competencies, _ in extracted for comp in competencies
        ]
        all_suggestions = list(category_result.suggested_new)
        suggestions: list[VacancyGraphSuggestion] = [
            self._category_suggestion_to_entity(vacancy.id, item)
            for item in all_suggestions
        ]
        for category, competencies, category_suggestions in extracted:
            category.competencies = competencies
            suggestions.extend(category_suggestions)
        category_nodes, competency_nodes, sub_nodes = _build_nodes_from_competencies(
            vacancy.id,
            all_competencies,
        )
        return _VacancyGraphPayload(
            categories=categories,
            competencies=all_competencies,
            category_nodes=category_nodes,
            competency_nodes=competency_nodes,
            sub_competency_nodes=sub_nodes,
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
        context: list[tuple[Category, _IdMapper, list[Competency]]] = []
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
            context.append((category, competency_mapper, existing_competencies))
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
        output: list[
            tuple[Category, list[Competency], list[VacancyGraphSuggestion]]
        ] = []
        for (category, mapper, existing_competencies), response in zip(
            context, responses, strict=False
        ):
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
                    "For new categories omit llm_id and provide "
                    "name/description/emoji/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
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
                    "For new competencies omit llm_id and provide "
                    "name/description/is_required/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
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
                    "You extract subcompetencies inside one competency for an IT "
                    "vacancy.\n"
                    "Return JSON only with keys: sub_competencies, suggested_new.\n"
                    "For existing subcompetencies always return llm_id.\n"
                    "For new subcompetencies omit llm_id and provide "
                    "name/description/target_level/weight/reason."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "vacancy": {
                            "name": vacancy.name,
                            "description": vacancy.description,
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
            category_id = (
                mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id)
                or uuid4()
            )
            catalog_item = mapper.get_item(category_id)
            categories.append(
                Category(
                    id=category_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description
                    or (catalog_item.description if catalog_item else ""),
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
            competency_id = (
                mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id)
                or uuid4()
            )
            catalog_item = mapper.get_item(competency_id)
            competencies.append(
                Competency(
                    id=competency_id,
                    category_id=suggestion.category_id or category_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description
                    or (catalog_item.description if catalog_item else ""),
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
            sub_id = (
                mapper.resolve_uuid(llm_id=suggestion.llm_id, direct_id=suggestion.id)
                or uuid4()
            )
            catalog_item = mapper.get_item(sub_id)
            subcompetencies.append(
                SubCompetency(
                    id=sub_id,
                    name=suggestion.name or (catalog_item.name if catalog_item else ""),
                    description=suggestion.description
                    or (catalog_item.description if catalog_item else ""),
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
            vacancy = await uow.vacancies.get(
                vacancy_id,
                include={VacancyInclude.NORMALIZED_GRAPH},
            )
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")

            payload = self._build_payload(graph)
            for node in payload.category_nodes:
                node.vacancy_id = vacancy.id
            for node in payload.competency_nodes:
                node.vacancy_id = vacancy.id
            for node in payload.sub_competency_nodes:
                node.vacancy_id = vacancy.id
            vacancy.status = VacancyStatus.READY
            vacancy.category_nodes = payload.category_nodes
            vacancy.competency_nodes = payload.competency_nodes
            vacancy.sub_competency_nodes = payload.sub_competency_nodes
            vacancy.error_message = graph.error_message

            used_category_names = {c.name.strip().lower() for c in payload.categories}
            used_competency_names = {
                c.name.strip().lower()
                for category in payload.categories
                for c in category.competencies
            }
            used_sub_names = {
                sub.name.strip().lower()
                for category in payload.categories
                for comp in category.competencies
                for sub in comp.sub_competencies
            }

            for decision in graph.suggestion_decisions:
                suggestion = await uow.vacancy_suggestions.get(decision.suggestion_id)
                if suggestion is None or suggestion.vacancy_id != vacancy_id:
                    continue
                suggestion.status = decision.status
                await uow.vacancy_suggestions.add(suggestion)

            suggestions = await uow.vacancy_suggestions.list_by_vacancy(vacancy_id)
            for suggestion in suggestions:
                if suggestion.status != SuggestionStatus.PENDING:
                    continue
                normalized_name = suggestion.name.strip().lower()
                if suggestion.stage == SuggestionStage.CATEGORY:
                    should_approve = normalized_name in used_category_names
                elif suggestion.stage == SuggestionStage.COMPETENCY:
                    should_approve = normalized_name in used_competency_names
                else:
                    should_approve = normalized_name in used_sub_names
                if should_approve:
                    suggestion.status = SuggestionStatus.APPROVED
                    await uow.vacancy_suggestions.add(suggestion)

            for category in payload.categories:
                await uow.categories.add(category)
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return _vacancy_to_dto(vacancy)

    def _build_payload(self, graph: VacancyGraphUpdateDTO) -> _VacancyGraphPayload:
        categories: list[Category] = []
        competencies: list[Competency] = []
        category_nodes: list[VacancyCategoryNode] = []
        competency_nodes: list[VacancyCompetencyNode] = []
        sub_nodes: list[VacancySubCompetencyNode] = []

        for category_position, category_dto in enumerate(graph.categories):
            category = Category(
                id=category_dto.id,
                name=category_dto.name,
                description=category_dto.description,
                emoji=category_dto.emoji,
            )
            category_nodes.append(
                VacancyCategoryNode(
                    id=uuid4(),
                    vacancy_id=UUID(int=0),
                    category_id=category.id,
                    position=category_position,
                )
            )
            category_competencies: list[Competency] = []
            for competency_dto in category_dto.competencies:
                competency = Competency(
                    id=competency_dto.id,
                    category_id=category.id,
                    name=competency_dto.name,
                    description=competency_dto.description,
                    sub_competencies=[
                        SubCompetency(
                            id=subcompetency_dto.id,
                            competency_id=competency_dto.id,
                            name=subcompetency_dto.name,
                            description=subcompetency_dto.description,
                            weight=subcompetency_dto.weight,
                        )
                        for subcompetency_dto in competency_dto.sub_competencies
                    ],
                )
                competency_nodes.append(
                    VacancyCompetencyNode(
                        id=uuid4(),
                        vacancy_id=UUID(int=0),
                        competency_id=competency.id,
                        category_id=category.id,
                        is_required=competency_dto.is_required,
                        position=len(competency_nodes),
                    )
                )
                for subcompetency_dto in competency_dto.sub_competencies:
                    sub_nodes.append(
                        VacancySubCompetencyNode(
                            id=uuid4(),
                            vacancy_id=UUID(int=0),
                            sub_competency_id=subcompetency_dto.id,
                            competency_id=competency.id,
                            target_level=subcompetency_dto.target_level,
                            weight=subcompetency_dto.weight,
                            position=len(sub_nodes),
                        )
                    )
                category_competencies.append(competency)
                competencies.append(competency)

            category.competencies = category_competencies
            categories.append(category)

        return _VacancyGraphPayload(
            categories=categories,
            competencies=competencies,
            category_nodes=category_nodes,
            competency_nodes=competency_nodes,
            sub_competency_nodes=sub_nodes,
            suggestions=[],
        )


class GetVacancyGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(
                vacancy_id,
                include={VacancyInclude.NORMALIZED_GRAPH},
            )
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

    async def execute(
        self, vacancy_id: UUID, decision: VacancySuggestionDecisionDTO
    ) -> VacancyGraphSuggestionDTO:
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


class ListVacanciesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        statuses: set[VacancyStatus],
    ) -> list[VacancyListItemDTO]:
        async with self._uow as uow:
            rows = await uow.vacancies.list_by_statuses(statuses)
            return [_vacancy_to_list_item(vacancy) for vacancy in rows]


class UpdateVacancyStatusUseCase:
    _ALLOWED_TRANSITIONS: dict[VacancyStatus, set[VacancyStatus]] = {
        VacancyStatus.DRAFT: {VacancyStatus.EXTRACTING, VacancyStatus.READY},
        VacancyStatus.EXTRACTING: {VacancyStatus.DRAFT, VacancyStatus.FAILED},
        VacancyStatus.READY: {VacancyStatus.DRAFT},
        VacancyStatus.FAILED: {VacancyStatus.DRAFT, VacancyStatus.EXTRACTING},
    }

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        vacancy_id: UUID,
        command: VacancyStatusUpdateDTO,
    ) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")
            allowed = self._ALLOWED_TRANSITIONS.get(vacancy.status, set())
            if command.status != vacancy.status and command.status not in allowed:
                raise ValueError(
                    "Invalid status transition: "
                    f"{vacancy.status.value} -> {command.status.value}"
                )
            vacancy.status = command.status
            if command.status != VacancyStatus.FAILED:
                vacancy.error_message = None
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return _vacancy_to_dto(vacancy)


class ListVacanciesForReviewUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[VacancyListItemDTO]:
        return await ListVacanciesUseCase(self._uow).execute(
            statuses={
                VacancyStatus.DRAFT,
                VacancyStatus.EXTRACTING,
                VacancyStatus.FAILED,
            }
        )
