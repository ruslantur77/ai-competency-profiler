from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from uuid import UUID, uuid4

from competency_system.application.dtos.mappers import (
    task_dto_from_domain,
    task_list_item_dto_from_domain,
)
from competency_system.application.dtos.pagination import PaginatedItemsDTO
from competency_system.application.dtos.task import (
    SyncTasksResultDTO,
    TaskDTO,
    TaskGraphCategoryInputDTO,
    TaskGraphCompetencyInputDTO,
    TaskGraphNodeMode,
    TaskGraphSubCompetencyInputDTO,
    TaskGraphUpdateDTO,
    TaskListItemDTO,
    TaskStatusUpdateDTO,
)
from competency_system.application.errors import NotFoundError, ValidationError
from competency_system.application.llm.llm_dispatch_payload import TaskExtractionPayload
from competency_system.application.llm.llm_orchestrator import StructuredLLMOrchestrator
from competency_system.application.llm.pipeline import (
    LLMSelectionCategoriesOutput,
    LLMSelectionCompetenciesOutput,
    LLMSelectionSubCompetenciesOutput,
    PipelineConfig,
    StageConfig,
    ThreeStagePipeline,
)
from competency_system.application.llm.prompts import PromptCatalog, ThreeStagePrompts
from competency_system.application.ports.external_testing_system import (
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.llm import LLMGateway
from competency_system.application.ports.llm_jobs import LLMJobQueuePort, LLMJobType
from competency_system.application.ports.repositories import (
    CategoryInclude,
    CompetencyInclude,
    TaskInclude,
)
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Task,
    TaskCategoryNode,
    TaskCompetencyNode,
    TaskSubCompetencyNode,
)
from competency_system.domain.value_objects.enums import TaskStatus

logger = logging.getLogger(__name__)


class _TaskGraphPayload:
    def __init__(
        self,
        *,
        category_nodes: list[TaskCategoryNode],
        competency_nodes: list[TaskCompetencyNode],
        sub_competency_nodes: list[TaskSubCompetencyNode],
    ) -> None:
        self.category_nodes = category_nodes
        self.competency_nodes = competency_nodes
        self.sub_competency_nodes = sub_competency_nodes


class _TaskGraphSavePayload:
    def __init__(
        self,
        *,
        categories: list[Category],
        competencies: list[Competency],
        sub_competencies: list[SubCompetency],
        category_nodes: list[TaskCategoryNode],
        competency_nodes: list[TaskCompetencyNode],
        sub_competency_nodes: list[TaskSubCompetencyNode],
    ) -> None:
        self.categories = categories
        self.competencies = competencies
        self.sub_competencies = sub_competencies
        self.category_nodes = category_nodes
        self.competency_nodes = competency_nodes
        self.sub_competency_nodes = sub_competency_nodes


def _build_nodes_from_competencies(
    task_id: UUID,
    competencies: list[Competency],
) -> _TaskGraphPayload:
    categories: dict[UUID, list[Competency]] = defaultdict(list)
    category_order: list[UUID] = []

    for comp in competencies:
        if comp.category_id not in categories:
            category_order.append(comp.category_id)
        categories[comp.category_id].append(comp)

    category_nodes = [
        TaskCategoryNode(
            id=uuid4(),
            task_id=task_id,
            category_id=category_id,
            position=position,
        )
        for position, category_id in enumerate(category_order)
    ]

    competency_nodes: list[TaskCompetencyNode] = []
    sub_nodes: list[TaskSubCompetencyNode] = []

    for category_id in category_order:
        comps = categories[category_id]

        for comp in comps:
            competency_nodes.append(
                TaskCompetencyNode(
                    id=uuid4(),
                    task_id=task_id,
                    competency_id=comp.id,
                    category_id=comp.category_id,
                    is_required=True,
                    position=len(competency_nodes),
                )
            )

            for sub in comp.sub_competencies:
                sub_nodes.append(
                    TaskSubCompetencyNode(
                        id=uuid4(),
                        task_id=task_id,
                        sub_competency_id=sub.id,
                        competency_id=comp.id,
                        target_level=sub.target_level,
                        weight=sub.weight,
                        position=len(sub_nodes),
                    )
                )

    return _TaskGraphPayload(
        category_nodes=category_nodes,
        competency_nodes=competency_nodes,
        sub_competency_nodes=sub_nodes,
    )


class MapTaskToCompetenciesOperation:
    def __init__(
        self,
        llm_gateway: LLMGateway,
        uow: UnitOfWork,
        *,
        max_mappings: int = 12,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
        prompt_version: str = "v1",
        prompt_catalog: PromptCatalog | None = None,
    ) -> None:
        self._uow = uow
        self._max_mappings = max_mappings
        self._llm_orchestrator = StructuredLLMOrchestrator(
            llm_gateway,
            max_parallel_requests=max_parallel_requests,
            stage_timeout_seconds=stage_timeout_seconds,
        )
        self._prompt_catalog = prompt_catalog or PromptCatalog()
        self._prompts: ThreeStagePrompts = self._prompt_catalog.get_task_prompts(
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

    async def run(self, task_id: UUID) -> None:
        task: Task | None = None
        try:
            async with self._uow as uow:
                task = await uow.tasks.get(
                    task_id,
                    include={TaskInclude.NORMALIZED_GRAPH},
                )
                if not task:
                    raise NotFoundError(f"Task {task_id} not found")
                categories = await uow.categories.get_list()

            competencies = await self._map(task, list(categories))
            payload = _build_nodes_from_competencies(task.id, competencies)
            task.category_nodes = payload.category_nodes
            task.competency_nodes = payload.competency_nodes
            task.sub_competency_nodes = payload.sub_competency_nodes
            task.status = TaskStatus.DRAFT
            task.error_message = None
        except Exception as exc:
            if not task:
                raise
            logger.exception(
                "llm_operation_failed",
                extra={
                    "operation": "map_task_to_competencies",
                    "status": "failed",
                    "task_id": str(task_id),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            task.category_nodes = []
            task.competency_nodes = []
            task.sub_competency_nodes = []
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)

        async with self._uow as uow:
            await uow.tasks.add(task)
            await uow.commit()

    async def _map(
        self,
        task: Task,
        categories: list[Category],
    ) -> list[Competency]:
        if not categories:
            return []

        subcompetencies, _ = await self.llm_pipeline.execute(
            categories=categories,
            competencies_by_category=self.competencies_by_category,
            sub_competencies_by_competency=self.sub_competencies_by_competency,
            payload=self._task_payload(task),
        )
        selected = sorted(subcompetencies, key=lambda item: item.weight)[
            : self._max_mappings
        ]
        dedup: dict[UUID, Competency] = {}
        for item in selected:
            if item.competency is None:
                continue
            comp = dedup.setdefault(
                item.competency.id,
                Competency(
                    id=item.competency.id,
                    category_id=item.competency.category_id,
                    name=item.competency.name,
                    description=item.competency.description,
                    sub_competencies=[],
                    created_at=item.competency.created_at,
                    updated_at=item.competency.updated_at,
                ),
            )
            comp.sub_competencies.append(item)

        return list(dedup.values())

    def _task_payload(self, task: Task) -> dict[str, object]:
        return {
            "title": task.title,
            "description": task.description,
        }


class SyncTasksUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        gateway: ExternalTestingSystemGateway,
        job_queue: LLMJobQueuePort,
    ) -> None:
        self._uow = uow
        self._gateway = gateway
        self._job_queue = job_queue

    async def execute(
        self,
        *,
        start: datetime,
        end: datetime,
        force: bool = False,
    ) -> SyncTasksResultDTO:
        del force
        external_tasks = await self._gateway.list_tasks(
            start=start,
            end=end,
            force=False,
        )

        async with self._uow as uow:
            synced: list[TaskDTO] = []

            for record in external_tasks:
                task = await uow.tasks.get_by_external_id(record.external_id)
                if task is None:
                    task = Task(
                        id=uuid4(),
                        external_id=record.external_id,
                        title=record.title,
                        description=record.description,
                        type=record.type,
                        status=TaskStatus.PENDING,
                    )
                    await uow.tasks.add(task)
                    await self._enqueue_mapping(task.id)
                    await uow.commit()

                synced.append(task_dto_from_domain(task))

        return SyncTasksResultDTO(synced_tasks=synced)

    async def _enqueue_mapping(self, task_id: UUID) -> None:
        await self._job_queue.enqueue(
            job_type=LLMJobType.TASK_MAPPING,
            payload=TaskExtractionPayload(task_id=task_id, raw_text="").model_dump(
                mode="json"
            ),
        )


class SaveTaskGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID, graph: TaskGraphUpdateDTO) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id, include={TaskInclude.NORMALIZED_GRAPH})
            if task is None:
                raise NotFoundError(f"Task {task_id} not found")
            payload = await self._build_payload(uow, graph)

            for node in payload.category_nodes:
                node.task_id = task.id
            for node in payload.competency_nodes:
                node.task_id = task.id
            for node in payload.sub_competency_nodes:
                node.task_id = task.id

            task.category_nodes = payload.category_nodes
            task.competency_nodes = payload.competency_nodes
            task.sub_competency_nodes = payload.sub_competency_nodes
            task.status = TaskStatus.DRAFT
            task.error_message = graph.error_message

            for category in payload.categories:
                await uow.categories.add(category)
            for competency in payload.competencies:
                await uow.competencies.add(competency)
            for sub_competency in payload.sub_competencies:
                await uow.sub_competencies.add(sub_competency)

            await uow.tasks.add(task)
            await uow.commit()
            return task_dto_from_domain(task)

    async def _build_payload(
        self,
        uow: UnitOfWork,
        graph: TaskGraphUpdateDTO,
    ) -> _TaskGraphSavePayload:
        categories_to_create: list[Category] = []
        competencies_to_create: list[Competency] = []
        sub_competencies_to_create: list[SubCompetency] = []
        category_nodes: list[TaskCategoryNode] = []
        competency_nodes: list[TaskCompetencyNode] = []
        sub_nodes: list[TaskSubCompetencyNode] = []
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
                TaskCategoryNode(
                    id=uuid4(),
                    task_id=UUID(int=0),
                    category_id=category.id,
                    position=category_position,
                )
            )
            if category_dto.mode == TaskGraphNodeMode.NEW:
                categories_to_create.append(category)

            for competency_dto in category_dto.competencies:
                competency = await self._resolve_competency(
                    uow,
                    competency_dto,
                    category_id=category.id,
                )
                if competency.id in used_competency_ids:
                    raise ValidationError(
                        f"Duplicate competency node for competency_id={competency.id}"
                    )
                used_competency_ids.add(competency.id)

                competency_nodes.append(
                    TaskCompetencyNode(
                        id=uuid4(),
                        task_id=UUID(int=0),
                        competency_id=competency.id,
                        category_id=category.id,
                        is_required=competency_dto.is_required,
                        position=len(competency_nodes),
                    )
                )
                if competency_dto.mode == TaskGraphNodeMode.NEW:
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
                        TaskSubCompetencyNode(
                            id=uuid4(),
                            task_id=UUID(int=0),
                            sub_competency_id=sub_competency.id,
                            competency_id=competency.id,
                            target_level=subcompetency_dto.target_level,
                            weight=subcompetency_dto.weight,
                            position=len(sub_nodes),
                        )
                    )
                    if subcompetency_dto.mode == TaskGraphNodeMode.NEW:
                        sub_competencies_to_create.append(sub_competency)

        return _TaskGraphSavePayload(
            categories=categories_to_create,
            competencies=competencies_to_create,
            sub_competencies=sub_competencies_to_create,
            category_nodes=category_nodes,
            competency_nodes=competency_nodes,
            sub_competency_nodes=sub_nodes,
        )

    async def _resolve_category(
        self,
        uow: UnitOfWork,
        category_dto: TaskGraphCategoryInputDTO,
    ) -> Category:
        if category_dto.mode == TaskGraphNodeMode.EXISTING:
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
        competency_dto: TaskGraphCompetencyInputDTO,
        *,
        category_id: UUID,
    ) -> Competency:
        if competency_dto.mode == TaskGraphNodeMode.EXISTING:
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
        subcompetency_dto: TaskGraphSubCompetencyInputDTO,
        *,
        competency_id: UUID,
    ) -> SubCompetency:
        if subcompetency_dto.mode == TaskGraphNodeMode.EXISTING:
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


class FinalizeTaskGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id, include={TaskInclude.NORMALIZED_GRAPH})
            if task is None:
                raise NotFoundError(f"Task {task_id} not found")
            if not task.sub_competency_nodes:
                raise ValidationError(
                    "Task graph must contain at least one sub-competency"
                )
            task.status = TaskStatus.READY
            task.error_message = None
            await uow.tasks.add(task)
            await uow.commit()
            return task_dto_from_domain(task)


class GetTaskGraphUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id, include={TaskInclude.NORMALIZED_GRAPH})
            if task is None:
                raise NotFoundError(f"Task {task_id} not found")
            return task_dto_from_domain(task)


class ListTasksUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        statuses: set[TaskStatus] | None,
        limit: int,
        offset: int,
    ) -> PaginatedItemsDTO[TaskListItemDTO]:
        async with self._uow as uow:
            rows = await uow.tasks.list_by_statuses(
                statuses, limit=limit, offset=offset
            )
            total = await uow.tasks.count_by_statuses(statuses)
            return PaginatedItemsDTO[TaskListItemDTO](
                items=[task_list_item_dto_from_domain(task) for task in rows],
                total=total,
                limit=limit,
                offset=offset,
            )


class UpdateTaskStatusUseCase:
    _ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.DRAFT: {TaskStatus.PENDING, TaskStatus.READY},
        TaskStatus.PENDING: {TaskStatus.DRAFT, TaskStatus.FAILED},
        TaskStatus.READY: {TaskStatus.DRAFT},
        TaskStatus.FAILED: {TaskStatus.DRAFT, TaskStatus.PENDING},
    }

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID, command: TaskStatusUpdateDTO) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                raise NotFoundError(f"Task {task_id} not found")
            allowed = self._ALLOWED_TRANSITIONS.get(task.status, set())
            if command.status != task.status and command.status not in allowed:
                raise ValidationError(
                    "Invalid status transition: "
                    f"{task.status.value} -> {command.status.value}"
                )
            task.status = command.status
            if command.status != TaskStatus.FAILED:
                task.error_message = None
            await uow.tasks.add(task)
            await uow.commit()
            return task_dto_from_domain(task)
