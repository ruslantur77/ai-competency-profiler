from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from competency_system.application.dtos.mappers import (
    suggestion_dto_from_domain,
    vacancy_dto_from_domain,
    vacancy_list_item_dto_from_domain,
)
from competency_system.application.dtos.pagination import PaginatedItemsDTO
from competency_system.application.dtos.vacancy import (
    VacancyCreateDTO,
    VacancyDTO,
    VacancyGraphCategoryInputDTO,
    VacancyGraphCompetencyInputDTO,
    VacancyGraphSubCompetencyInputDTO,
    VacancyGraphSuggestionDTO,
    VacancyGraphUpdateDTO,
    VacancyListItemDTO,
    VacancyStatusUpdateDTO,
    VacancySuggestionBulkDecisionDTO,
    VacancySuggestionDecisionDTO,
    VacancyUpdateDTO,
)
from competency_system.application.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from competency_system.application.llm.llm_dispatch_payload import (
    VacancyExtractionPayload,
)
from competency_system.application.llm.llm_orchestrator import (
    StructuredLLMOrchestrator,
)
from competency_system.application.llm.pipeline import (
    LLMSelectionCategoriesOutput,
    LLMSelectionCompetenciesOutput,
    LLMSelectionSubCompetenciesOutput,
    PipelineConfig,
    StageConfig,
    ThreeStagePipeline,
)
from competency_system.application.llm.prompts import PromptCatalog, ThreeStagePrompts
from competency_system.application.ports.llm import LLMGateway
from competency_system.application.ports.llm_jobs import LLMJobQueuePort, LLMJobType
from competency_system.application.ports.repositories import (
    CategoryInclude,
    CompetencyInclude,
    VacancyInclude,
)
from competency_system.application.ports.uow import UnitOfWork
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
    SuggestionStage,
    SuggestionStatus,
    VacancyStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class _VacancyGraphPayload:
    categories: list[Category]
    competencies: list[Competency]
    sub_competencies: list[SubCompetency]
    category_nodes: list[VacancyCategoryNode]
    competency_nodes: list[VacancyCompetencyNode]
    sub_competency_nodes: list[VacancySubCompetencyNode]
    suggestions: list[VacancyGraphSuggestion]


async def _get_vacancy_for_mutation(
    uow: UnitOfWork,
    vacancy_id: UUID,
    *,
    include_graph: bool = False,
) -> Vacancy:
    include = {VacancyInclude.NORMALIZED_GRAPH} if include_graph else None
    vacancy = await uow.vacancies.get(vacancy_id, include=include)
    if vacancy is not None:
        return vacancy
    deleted = await uow.vacancies.get(
        vacancy_id,
        include=include,
        include_deleted=True,
    )
    if deleted is not None and deleted.deleted_at is not None:
        raise ConflictError(f"Vacancy {vacancy_id} is deleted")
    raise NotFoundError(f"Vacancy {vacancy_id} not found")


def _map_category_node(
    vacancy_id: UUID, category_id: UUID, position: int
) -> VacancyCategoryNode:
    return VacancyCategoryNode(
        id=uuid4(),
        vacancy_id=vacancy_id,
        category_id=category_id,
        position=position,
    )


def _map_competency_node(
    vacancy_id: UUID,
    competency: Competency,
    position: int,
) -> VacancyCompetencyNode:
    return VacancyCompetencyNode(
        id=uuid4(),
        vacancy_id=vacancy_id,
        competency_id=competency.id,
        category_id=competency.category_id,
        is_required=True,
        position=position,
    )


def _map_sub_competency_node(
    vacancy_id: UUID,
    competency: Competency,
    sub: SubCompetency,
    position: int,
) -> VacancySubCompetencyNode:
    return VacancySubCompetencyNode(
        id=uuid4(),
        vacancy_id=vacancy_id,
        sub_competency_id=sub.id,
        competency_id=competency.id,
        target_level=sub.target_level,
        weight=sub.weight,
        position=position,
    )


def _build_nodes_from_competencies(
    vacancy_id: UUID,
    competencies: list[Competency],
) -> tuple[
    list[VacancyCategoryNode],
    list[VacancyCompetencyNode],
    list[VacancySubCompetencyNode],
]:
    categories: dict[UUID, list[Competency]] = defaultdict(list)
    category_order: list[UUID] = []

    for comp in competencies:
        if comp.category_id not in categories:
            category_order.append(comp.category_id)
        categories[comp.category_id].append(comp)

    category_nodes = [
        _map_category_node(vacancy_id, category_id, position)
        for position, category_id in enumerate(category_order)
    ]

    competency_nodes: list[VacancyCompetencyNode] = []
    sub_nodes: list[VacancySubCompetencyNode] = []

    for category_id in category_order:
        comps = categories[category_id]

        for comp_pos, comp in enumerate(comps):
            competency_nodes.append(_map_competency_node(vacancy_id, comp, comp_pos))

            for sub_pos, sub in enumerate(comp.sub_competencies):
                sub_nodes.append(
                    _map_sub_competency_node(vacancy_id, comp, sub, sub_pos)
                )

    return category_nodes, competency_nodes, sub_nodes


class CreateVacancyGraphUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        job_queue: LLMJobQueuePort,
    ) -> None:
        self._uow = uow
        self._job_queue = job_queue

    async def execute(self, command: VacancyCreateDTO) -> VacancyDTO:
        vacancy = Vacancy(
            name=command.name,
            description=command.description,
            status=VacancyStatus.PENDING,
        )
        async with self._uow as uow:
            await uow.vacancies.add(vacancy)
            await uow.commit()
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.VACANCY_EXTRACTION,
            payload=VacancyExtractionPayload(
                vacancy_id=vacancy.id, raw_text=vacancy.description
            ).model_dump(mode="json"),
        )
        return vacancy_dto_from_domain(vacancy)


class ExtractVacancyGraphOperation:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: LLMGateway,
        *,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
        max_suggested_new_per_stage: int = 5,
        prompt_version: str = "v1",
        prompt_catalog: PromptCatalog | None = None,
    ) -> None:
        self._uow = uow
        self._llm_orchestrator = StructuredLLMOrchestrator(
            llm_gateway,
            max_parallel_requests=max_parallel_requests,
            stage_timeout_seconds=stage_timeout_seconds,
        )
        self._max_suggested_new_per_stage = max(0, max_suggested_new_per_stage)
        self._prompt_catalog = prompt_catalog or PromptCatalog()
        self._prompts: ThreeStagePrompts = self._prompt_catalog.get_vacancy_prompts(
            prompt_version
        )

        self.llm_pipeline: ThreeStagePipeline[
            LLMSelectionCategoriesOutput,
            LLMSelectionCompetenciesOutput,
            LLMSelectionSubCompetenciesOutput,
        ] = ThreeStagePipeline(
            orchestrator=self._llm_orchestrator,
            config=PipelineConfig(
                stage1=StageConfig(
                    system_prompt=self._prompts.step1_categories,
                    response_model=LLMSelectionCategoriesOutput,
                    temperature=0.1,
                ),
                stage2=StageConfig(
                    system_prompt=self._prompts.step2_competencies,
                    response_model=LLMSelectionCompetenciesOutput,
                    temperature=0.1,
                ),
                stage3=StageConfig(
                    system_prompt=self._prompts.step3_subcompetencies,
                    response_model=LLMSelectionSubCompetenciesOutput,
                    temperature=0.1,
                ),
                category_to_dict=lambda category: {
                    "name": category.name,
                    "description": category.description,
                },
                competency_to_dict=lambda competency: {
                    "name": competency.name,
                    "description": competency.description,
                },
                sub_competency_to_dict=lambda sub: {
                    "name": sub.name,
                    "description": sub.description,
                },
            ),
        )

    async def competencies_by_category(self, category_id: UUID) -> list[Competency]:
        async with self._uow as uow:
            category = await uow.categories.get(
                category_id, include={CategoryInclude.COMPETENCIES}
            )
            return category.competencies if category else []

    async def sub_competencies_by_competency(
        self, competency_id: UUID
    ) -> list[SubCompetency]:
        async with self._uow as uow:
            competency = await uow.competencies.get(
                competency_id, include={CompetencyInclude.SUB_COMPETENCIES}
            )
            return competency.sub_competencies if competency else []

    async def run(self, vacancy_id: UUID) -> None:
        vacancy: Vacancy | None = None
        try:
            async with self._uow as uow:
                vacancy = await uow.vacancies.get(vacancy_id)
                if vacancy is None:
                    return
                existing_categories = list(
                    await uow.categories.get_list(
                        include={CategoryInclude.SUB_COMPETENCIES}
                    )
                )
            graph = await self._map(vacancy, existing_categories)
            vacancy.status = VacancyStatus.DRAFT
            vacancy.category_nodes = graph.category_nodes
            vacancy.competency_nodes = graph.competency_nodes
            vacancy.sub_competency_nodes = graph.sub_competency_nodes
            vacancy.error_message = None

            async with self._uow as uow:
                await uow.vacancies.add(vacancy)
                for suggestion in graph.suggestions:
                    suggestion.vacancy_id = vacancy.id
                    await uow.vacancy_suggestions.add(suggestion)
                await uow.commit()
            logger.info(
                "llm_operation_finished",
                extra={
                    "operation": "extract_vacancy_graph",
                    "status": "success",
                    "vacancy_id": str(vacancy_id),
                    "category_nodes_count": len(vacancy.category_nodes),
                    "competency_nodes_count": len(vacancy.competency_nodes),
                    "sub_competency_nodes_count": len(vacancy.sub_competency_nodes),
                    "suggestions_count": len(graph.suggestions),
                },
            )
        except Exception as exc:
            if not vacancy:
                raise
            logger.exception(
                "llm_operation_failed",
                extra={
                    "operation": "extract_vacancy_graph",
                    "status": "failed",
                    "vacancy_id": str(vacancy_id),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            vacancy.status = VacancyStatus.FAILED
            vacancy.error_message = str(exc)
            async with self._uow as uow:
                await uow.vacancies.add(vacancy)
                await uow.commit()

    async def _map(
        self,
        vacancy: Vacancy,
        categories: list[Category],
    ) -> _VacancyGraphPayload:
        if not categories:
            return _VacancyGraphPayload(
                categories=[],
                competencies=[],
                sub_competencies=[],
                category_nodes=[],
                competency_nodes=[],
                sub_competency_nodes=[],
                suggestions=[],
            )

        subcompetencies, suggestions = await self.llm_pipeline.execute(
            categories=categories,
            competencies_by_category=self.competencies_by_category,
            sub_competencies_by_competency=self.sub_competencies_by_competency,
            payload=self._vacancy_payload(vacancy),
        )
        competencies = list({comp for i in subcompetencies if (comp := i.competency)})
        category_nodes, competency_nodes, sub_nodes = _build_nodes_from_competencies(
            vacancy.id, competencies
        )

        return _VacancyGraphPayload(
            categories=categories,
            competencies=competencies,
            sub_competencies=[
                sub
                for competency in competencies
                for sub in competency.sub_competencies
            ],
            category_nodes=category_nodes,
            competency_nodes=competency_nodes,
            sub_competency_nodes=sub_nodes,
            suggestions=suggestions,
        )

    @staticmethod
    def _vacancy_payload(vacancy: Vacancy) -> dict[str, object]:
        return {
            "name": vacancy.name,
            "description": vacancy.description,
        }


class SaveVacancyGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        vacancy_id: UUID,
        graph: VacancyGraphUpdateDTO,
    ) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await _get_vacancy_for_mutation(
                uow,
                vacancy_id,
                include_graph=True,
            )

            payload = await self._build_payload(uow, graph)
            for cat_node in payload.category_nodes:
                cat_node.vacancy_id = vacancy.id
            for comp_node in payload.competency_nodes:
                comp_node.vacancy_id = vacancy.id
            for sub_node in payload.sub_competency_nodes:
                sub_node.vacancy_id = vacancy.id
            vacancy.category_nodes = payload.category_nodes
            vacancy.competency_nodes = payload.competency_nodes
            vacancy.sub_competency_nodes = payload.sub_competency_nodes
            vacancy.error_message = graph.error_message

            for category in payload.categories:
                await uow.categories.add(category)
            for competency in payload.competencies:
                await uow.competencies.add(competency)
            for sub_competency in payload.sub_competencies:
                await uow.sub_competencies.add(sub_competency)
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return vacancy_dto_from_domain(vacancy)

    async def _build_payload(
        self, uow: UnitOfWork, graph: VacancyGraphUpdateDTO
    ) -> _VacancyGraphPayload:
        categories_to_create: list[Category] = []
        competencies_to_create: list[Competency] = []
        sub_competencies_to_create: list[SubCompetency] = []
        category_nodes: list[VacancyCategoryNode] = []
        competency_nodes: list[VacancyCompetencyNode] = []
        sub_nodes: list[VacancySubCompetencyNode] = []
        used_category_ids: set[UUID] = set()
        used_competency_ids: set[UUID] = set()
        used_sub_competency_ids: set[UUID] = set()

        for category_position, category_dto in enumerate(graph.categories):
            category = await self._resolve_category(uow, category_dto)
            if category.id in used_category_ids:
                raise ValidationError(
                    f"Duplicate category node for category_id={category.id}"
                )
            used_category_ids.add(category.id)

            category_nodes.append(
                VacancyCategoryNode(
                    id=uuid4(),
                    vacancy_id=UUID(int=0),
                    category_id=category.id,
                    position=category_position,
                )
            )
            if category_dto.mode == "new":
                categories_to_create.append(category)

            for competency_dto in category_dto.competencies:
                competency = await self._resolve_competency(
                    uow, competency_dto, category_id=category.id
                )
                if competency.id in used_competency_ids:
                    raise ValidationError(
                        f"Duplicate competency node for competency_id={competency.id}"
                    )
                used_competency_ids.add(competency.id)

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

                if competency_dto.mode == "new":
                    competencies_to_create.append(competency)

                for subcompetency_dto in competency_dto.sub_competencies:
                    sub_competency = await self._resolve_sub_competency(
                        uow,
                        subcompetency_dto,
                        competency_id=competency.id,
                    )
                    if sub_competency.id in used_sub_competency_ids:
                        raise ValidationError(
                            "Duplicate sub-competency node for "
                            f"sub_competency_id={sub_competency.id}"
                        )
                    used_sub_competency_ids.add(sub_competency.id)

                    sub_nodes.append(
                        VacancySubCompetencyNode(
                            id=uuid4(),
                            vacancy_id=UUID(int=0),
                            sub_competency_id=sub_competency.id,
                            competency_id=competency.id,
                            target_level=subcompetency_dto.target_level,
                            weight=subcompetency_dto.weight,
                            position=len(sub_nodes),
                        )
                    )
                    if subcompetency_dto.mode == "new":
                        sub_competencies_to_create.append(sub_competency)

        return _VacancyGraphPayload(
            categories=categories_to_create,
            competencies=competencies_to_create,
            sub_competencies=sub_competencies_to_create,
            category_nodes=category_nodes,
            competency_nodes=competency_nodes,
            sub_competency_nodes=sub_nodes,
            suggestions=[],
        )

    async def _resolve_category(
        self,
        uow: UnitOfWork,
        category_dto: VacancyGraphCategoryInputDTO,
    ) -> Category:
        if category_dto.mode == "existing":
            if category_dto.id is None:
                raise ValidationError("Existing category requires id")
            category = await uow.categories.get(category_dto.id)
            if category is None:
                raise NotFoundError(f"Category {category_dto.id} not found")
            return category
        return Category(
            id=uuid4(),
            name=(category_dto.name or "").strip(),
            description=category_dto.description or "",
            emoji=category_dto.emoji or "",
        )

    async def _resolve_competency(
        self,
        uow: UnitOfWork,
        competency_dto: VacancyGraphCompetencyInputDTO,
        *,
        category_id: UUID,
    ) -> Competency:
        if competency_dto.mode == "existing":
            if competency_dto.id is None:
                raise ValidationError("Existing competency requires id")
            competency = await uow.competencies.get(competency_dto.id)
            if competency is None:
                raise NotFoundError(f"Competency {competency_dto.id} not found")
            if competency.category_id != category_id:
                raise ValidationError(
                    "Existing competency does not belong to the selected category"
                )
            return competency
        return Competency(
            id=uuid4(),
            category_id=category_id,
            name=(competency_dto.name or "").strip(),
            description=competency_dto.description or "",
            sub_competencies=[],
        )

    async def _resolve_sub_competency(
        self,
        uow: UnitOfWork,
        subcompetency_dto: VacancyGraphSubCompetencyInputDTO,
        *,
        competency_id: UUID,
    ) -> SubCompetency:
        if subcompetency_dto.mode == "existing":
            if subcompetency_dto.id is None:
                raise ValidationError("Existing sub-competency requires id")
            sub_competency = await uow.sub_competencies.get(subcompetency_dto.id)
            if sub_competency is None:
                raise NotFoundError(f"Sub-competency {subcompetency_dto.id} not found")
            if sub_competency.competency_id != competency_id:
                raise ValidationError(
                    "Existing sub-competency does not belong to the selected competency"
                )
            return sub_competency
        return SubCompetency(
            id=uuid4(),
            competency_id=competency_id,
            name=(subcompetency_dto.name or "").strip(),
            description=subcompetency_dto.description or "",
            weight=subcompetency_dto.weight,
            target_level=subcompetency_dto.target_level,
        )


class FinalizeVacancyGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await _get_vacancy_for_mutation(
                uow,
                vacancy_id,
                include_graph=True,
            )

            vacancy.status = VacancyStatus.READY
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return vacancy_dto_from_domain(vacancy)


class UpdateVacancyUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID, command: VacancyUpdateDTO) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await _get_vacancy_for_mutation(uow, vacancy_id)
            name = command.name.strip()
            if not name:
                raise ValidationError("Vacancy name must not be empty")
            vacancy.name = name
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return vacancy_dto_from_domain(vacancy)


class DeleteVacancyUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> None:
        async with self._uow as uow:
            deleted = await uow.vacancies.soft_delete(vacancy_id)
            if deleted is None:
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            await uow.commit()


class RestoreVacancyUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> VacancyDTO:
        async with self._uow as uow:
            restored = await uow.vacancies.restore(vacancy_id)
            if restored is None:
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            await uow.commit()
            return vacancy_dto_from_domain(restored)


class HardDeleteVacancyUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> None:
        async with self._uow as uow:
            existing = await uow.vacancies.get(vacancy_id, include_deleted=True)
            if existing is None:
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            await uow.vacancies.hard_delete(vacancy_id)
            await uow.commit()


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
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            return vacancy_dto_from_domain(vacancy)


class ListVacancySuggestionsUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, vacancy_id: UUID) -> list[VacancyGraphSuggestionDTO]:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise NotFoundError(f"Vacancy {vacancy_id} not found")
            suggestions = await uow.vacancy_suggestions.list_by_vacancy(vacancy_id)
            return [
                suggestion_dto_from_domain(suggestion) for suggestion in suggestions
            ]


class _VacancySuggestionApprovalHelper:
    @staticmethod
    def _next_position(nodes: Sequence[object]) -> int:
        if not nodes:
            return 0
        return max(getattr(node, "position", 0) for node in nodes) + 1

    async def _apply_approved_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        if suggestion.stage == SuggestionStage.CATEGORY:
            await self._apply_category_suggestion(uow, vacancy, suggestion)
            return
        if suggestion.stage == SuggestionStage.COMPETENCY:
            await self._apply_competency_suggestion(uow, vacancy, suggestion)
            return
        await self._apply_sub_competency_suggestion(uow, vacancy, suggestion)

    async def _apply_category_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        category = Category(
            id=uuid4(),
            name=suggestion.name,
            description=suggestion.description,
            emoji="",
        )
        await uow.categories.add(category)
        self._ensure_category_node(vacancy, category.id)

    async def _apply_competency_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        parent_category_id = suggestion.parent_category_id
        if parent_category_id is None:
            raise ValidationError("Competency suggestion is missing parent_category_id")
        parent_category = await uow.categories.get(parent_category_id)
        if parent_category is None:
            raise NotFoundError(f"Parent category {parent_category_id} not found")

        competency = Competency(
            id=uuid4(),
            category_id=parent_category.id,
            name=suggestion.name,
            description=suggestion.description,
            sub_competencies=[],
        )
        await uow.competencies.add(competency)

        self._ensure_category_node(vacancy, parent_category.id)
        self._ensure_competency_node(
            vacancy,
            competency.id,
            parent_category.id,
            is_required=suggestion.is_required
            if suggestion.is_required is not None
            else True,
        )

    async def _apply_sub_competency_suggestion(
        self,
        uow: UnitOfWork,
        vacancy: Vacancy,
        suggestion: VacancyGraphSuggestion,
    ) -> None:
        parent_competency_id = suggestion.parent_competency_id
        if parent_competency_id is None:
            raise ValidationError(
                "Sub-competency suggestion is missing parent_competency_id"
            )
        parent_competency = await uow.competencies.get(parent_competency_id)
        if parent_competency is None:
            raise NotFoundError(f"Parent competency {parent_competency_id} not found")

        target_level = suggestion.target_level or CompetencyLevel.BEGINNER
        weight = suggestion.weight if suggestion.weight is not None else 1.0
        sub_competency = SubCompetency(
            id=uuid4(),
            competency_id=parent_competency.id,
            name=suggestion.name,
            description=suggestion.description,
            weight=weight,
            target_level=target_level,
        )
        await uow.sub_competencies.add(sub_competency)

        self._ensure_category_node(vacancy, parent_competency.category_id)
        self._ensure_competency_node(
            vacancy,
            parent_competency.id,
            parent_competency.category_id,
            is_required=True,
        )
        self._ensure_sub_competency_node(
            vacancy,
            sub_competency.id,
            parent_competency.id,
            target_level=target_level,
            weight=weight,
        )

    def _ensure_category_node(self, vacancy: Vacancy, category_id: UUID) -> None:
        if any(node.category_id == category_id for node in vacancy.category_nodes):
            return
        vacancy.category_nodes.append(
            VacancyCategoryNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                category_id=category_id,
                position=self._next_position(vacancy.category_nodes),
            )
        )

    def _ensure_competency_node(
        self,
        vacancy: Vacancy,
        competency_id: UUID,
        category_id: UUID,
        *,
        is_required: bool,
    ) -> None:
        if any(
            node.competency_id == competency_id for node in vacancy.competency_nodes
        ):
            return
        vacancy.competency_nodes.append(
            VacancyCompetencyNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                competency_id=competency_id,
                category_id=category_id,
                is_required=is_required,
                position=self._next_position(vacancy.competency_nodes),
            )
        )

    def _ensure_sub_competency_node(
        self,
        vacancy: Vacancy,
        sub_competency_id: UUID,
        competency_id: UUID,
        *,
        target_level: CompetencyLevel,
        weight: float,
    ) -> None:
        if any(
            node.sub_competency_id == sub_competency_id
            for node in vacancy.sub_competency_nodes
        ):
            return
        vacancy.sub_competency_nodes.append(
            VacancySubCompetencyNode(
                id=uuid4(),
                vacancy_id=vacancy.id,
                sub_competency_id=sub_competency_id,
                competency_id=competency_id,
                target_level=target_level,
                weight=weight,
                position=self._next_position(vacancy.sub_competency_nodes),
            )
        )


class DecideVacancySuggestionUseCase(_VacancySuggestionApprovalHelper):
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, vacancy_id: UUID, decision: VacancySuggestionDecisionDTO
    ) -> VacancyGraphSuggestionDTO:
        if decision.status == SuggestionStatus.PENDING:
            raise ValidationError("Decision status must be approved or rejected")
        async with self._uow as uow:
            await _get_vacancy_for_mutation(uow, vacancy_id)
            suggestion = await uow.vacancy_suggestions.get(decision.suggestion_id)
            if suggestion is None or suggestion.vacancy_id != vacancy_id:
                raise NotFoundError(f"Suggestion {decision.suggestion_id} not found")

            if decision.status == SuggestionStatus.APPROVED:
                vacancy = await uow.vacancies.get(
                    vacancy_id,
                    include={VacancyInclude.NORMALIZED_GRAPH},
                )
                if vacancy is None:
                    raise NotFoundError(f"Vacancy {vacancy_id} not found")
                if suggestion.status != SuggestionStatus.APPROVED:
                    await self._apply_approved_suggestion(uow, vacancy, suggestion)
                await uow.vacancies.add(vacancy)

            suggestion.status = decision.status
            await uow.vacancy_suggestions.add(suggestion)
            await uow.commit()
            return suggestion_dto_from_domain(suggestion)


class DecideVacancySuggestionsUseCase(_VacancySuggestionApprovalHelper):
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        vacancy_id: UUID,
        command: VacancySuggestionBulkDecisionDTO,
    ) -> list[VacancyGraphSuggestionDTO]:
        async with self._uow as uow:
            await _get_vacancy_for_mutation(uow, vacancy_id)
            vacancy: Vacancy | None = None
            vacancy_changed = False
            results: list[VacancyGraphSuggestionDTO] = []

            for decision in command.decisions:
                if decision.status == SuggestionStatus.PENDING:
                    raise ValidationError(
                        "Decision status must be approved or rejected"
                    )

                suggestion = await uow.vacancy_suggestions.get(decision.suggestion_id)
                if suggestion is None or suggestion.vacancy_id != vacancy_id:
                    raise NotFoundError(
                        f"Suggestion {decision.suggestion_id} not found"
                    )

                if (
                    decision.status == SuggestionStatus.APPROVED
                    and suggestion.status != SuggestionStatus.APPROVED
                ):
                    if vacancy is None:
                        vacancy = await uow.vacancies.get(
                            vacancy_id,
                            include={VacancyInclude.NORMALIZED_GRAPH},
                        )
                        if vacancy is None:
                            raise NotFoundError(f"Vacancy {vacancy_id} not found")
                    await self._apply_approved_suggestion(uow, vacancy, suggestion)
                    vacancy_changed = True

                suggestion.status = decision.status
                await uow.vacancy_suggestions.add(suggestion)
                results.append(suggestion_dto_from_domain(suggestion))

            if vacancy_changed and vacancy is not None:
                await uow.vacancies.add(vacancy)

            await uow.commit()
            return results


class ListVacanciesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        statuses: set[VacancyStatus] | None = None,
        limit: int,
        offset: int,
    ) -> PaginatedItemsDTO[VacancyListItemDTO]:
        async with self._uow as uow:
            rows = await uow.vacancies.list_by_statuses(
                statuses,
                limit=limit,
                offset=offset,
            )
            total = await uow.vacancies.count_by_statuses(statuses)
            return PaginatedItemsDTO[VacancyListItemDTO](
                items=[vacancy_list_item_dto_from_domain(vacancy) for vacancy in rows],
                total=total,
                limit=limit,
                offset=offset,
            )


class UpdateVacancyStatusUseCase:
    _ALLOWED_TRANSITIONS: dict[VacancyStatus, set[VacancyStatus]] = {
        VacancyStatus.DRAFT: {VacancyStatus.PENDING, VacancyStatus.READY},
        VacancyStatus.PENDING: {VacancyStatus.DRAFT, VacancyStatus.FAILED},
        VacancyStatus.READY: {VacancyStatus.DRAFT},
        VacancyStatus.FAILED: {VacancyStatus.DRAFT, VacancyStatus.PENDING},
    }

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        vacancy_id: UUID,
        command: VacancyStatusUpdateDTO,
    ) -> VacancyDTO:
        async with self._uow as uow:
            vacancy = await _get_vacancy_for_mutation(
                uow, vacancy_id, include_graph=True
            )
            allowed = self._ALLOWED_TRANSITIONS.get(vacancy.status, set())
            if command.status != vacancy.status and command.status not in allowed:
                raise ValidationError(
                    "Invalid status transition: "
                    f"{vacancy.status.value} -> {command.status.value}"
                )
            vacancy.status = command.status
            if command.status != VacancyStatus.FAILED:
                vacancy.error_message = None
            await uow.vacancies.add(vacancy)
            await uow.commit()
            return vacancy_dto_from_domain(vacancy)


class ListVacanciesForReviewUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, limit: int, offset: int
    ) -> PaginatedItemsDTO[VacancyListItemDTO]:
        return await ListVacanciesUseCase(self._uow).execute(
            statuses={
                VacancyStatus.DRAFT,
                VacancyStatus.PENDING,
                VacancyStatus.FAILED,
            },
            limit=limit,
            offset=offset,
        )
