from __future__ import annotations

import json
from collections import defaultdict
from uuid import UUID, uuid4

from competency_system.application.dtos.task import (
    SyncTasksResultDTO,
    TaskCategoryExtractionResultDTO,
    TaskCategorySelectionDTO,
    TaskCompetencyExtractionResultDTO,
    TaskCompetencyMappingDTO,
    TaskCompetencySelectionDTO,
    TaskDTO,
    TaskSubCompetencyExtractionResultDTO,
    TaskSubCompetencySelectionDTO,
)
from competency_system.application.ports.external_testing_system import (
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.llm_jobs import LLMJobQueuePort, LLMJobType
from competency_system.application.ports.repositories import (
    CategoryInclude,
    TaskInclude,
)
from competency_system.application.ports.uow import UnitOfWork
from competency_system.application.prompts import PromptCatalog, ThreeStagePrompts
from competency_system.application.use_cases.llm_orchestrator import (
    LLMCallSpec,
    StructuredLLMOrchestrator,
)
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Task,
    TaskCompetencyMapping,
)
from competency_system.domain.value_objects.enums import TaskMappingStatus


def _task_to_dto(task: Task) -> TaskDTO:
    return TaskDTO(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=task.type,
        competency_mappings=[
            TaskCompetencyMappingDTO(
                sub_competency_id=mapping.sub_competency_id,
                weight=mapping.weight,
            )
            for mapping in task.competency_mappings
        ],
        mapping_validated=task.mapping_validated,
        mapping_status=task.mapping_status,
        mapping_error_message=task.mapping_error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


class MapTaskToCompetenciesUseCase:
    def __init__(
        self,
        llm_gateway: LLMGateway,
        *,
        max_mappings: int = 12,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
        prompt_version: str = "v1",
        prompt_catalog: PromptCatalog | None = None,
    ) -> None:
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

    async def execute(
        self,
        task: Task,
        categories: list[Category],
        *,
        tags: list[str] | None = None,
    ) -> list[TaskCompetencyMapping]:
        if not categories:
            return []

        selected_categories = await self._select_categories(
            task,
            categories,
            tags=tags or [],
        )
        if not selected_categories:
            return []

        selected_competencies = await self._select_competencies(
            task, selected_categories, tags or []
        )
        if not selected_competencies:
            return []

        response = await self._select_subcompetencies(
            task, selected_competencies, tags or []
        )
        subcompetencies = [
            sub
            for competency in selected_competencies
            for sub in competency.sub_competencies
        ]
        return self._normalize_mappings(response, subcompetencies)

    async def _select_categories(
        self,
        task: Task,
        categories: list[Category],
        *,
        tags: list[str],
    ) -> list[Category]:
        response = await self._llm_orchestrator.run(
            LLMCallSpec(
                stage="task_categories",
                messages=self._category_messages(task, categories, tags),
                response_model=TaskCategoryExtractionResultDTO,
                temperature=0.1,
            )
        )
        selected_ids = self._resolve_ids(response.categories, categories)
        return [category for category in categories if category.id in selected_ids]

    async def _select_competencies(
        self,
        task: Task,
        categories: list[Category],
        tags: list[str],
    ) -> list[Competency]:
        specs: list[LLMCallSpec[TaskCompetencyExtractionResultDTO]] = []
        context: list[Category] = []
        for category in categories:
            if not category.competencies:
                continue
            context.append(category)
            specs.append(
                LLMCallSpec(
                    stage="task_competencies",
                    messages=self._competency_messages(task, category, tags),
                    response_model=TaskCompetencyExtractionResultDTO,
                    temperature=0.1,
                )
            )
        responses = await self._llm_orchestrator.run_many(specs)
        selected: list[Competency] = []
        for category, response in zip(context, responses, strict=False):
            selected_ids = self._resolve_ids(
                response.competencies,
                category.competencies,
            )
            selected.extend(
                competency
                for competency in category.competencies
                if competency.id in selected_ids
            )
        return selected

    async def _select_subcompetencies(
        self,
        task: Task,
        competencies: list[Competency],
        tags: list[str],
    ) -> TaskSubCompetencyExtractionResultDTO:
        specs: list[LLMCallSpec[TaskSubCompetencyExtractionResultDTO]] = []
        context: list[Competency] = []
        for competency in competencies:
            if not competency.sub_competencies:
                continue
            context.append(competency)
            specs.append(
                LLMCallSpec(
                    stage="task_subcompetencies",
                    messages=self._subcompetency_messages(task, competency, tags),
                    response_model=TaskSubCompetencyExtractionResultDTO,
                    temperature=0.1,
                )
            )
        responses = await self._llm_orchestrator.run_many(specs)

        payload: list[TaskCompetencyMappingDTO] = []
        for competency, response in zip(context, responses, strict=False):
            resolved_ids = self._resolve_ids(
                response.sub_competencies,
                competency.sub_competencies,
            )
            sub_by_id = {sub.id: sub for sub in competency.sub_competencies}
            for item in response.sub_competencies:
                sub_id = self._resolve_single_id(
                    item.id,
                    item.llm_id,
                    competency.sub_competencies,
                )
                if (
                    sub_id is None
                    or sub_id not in resolved_ids
                    or sub_id not in sub_by_id
                ):
                    continue
                payload.append(
                    TaskCompetencyMappingDTO(
                        sub_competency_id=sub_id,
                        weight=item.weight,
                    )
                )
        return TaskSubCompetencyExtractionResultDTO(
            sub_competencies=[
                TaskSubCompetencySelectionDTO(
                    id=item.sub_competency_id,
                    weight=item.weight,
                )
                for item in payload
            ]
        )

    def _competency_messages(
        self,
        task: Task,
        category: Category,
        tags: list[str],
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=self._prompts.step2_competencies,
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": self._task_payload(task, tags),
                        "category": {
                            "id": str(category.id),
                            "name": category.name,
                            "description": category.description,
                        },
                        "available_competencies": [
                            {
                                "llm_id": index,
                                "id": str(competency.id),
                                "name": competency.name,
                                "description": competency.description,
                            }
                            for index, competency in enumerate(
                                category.competencies, start=1
                            )
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _subcompetency_messages(
        self,
        task: Task,
        competency: Competency,
        tags: list[str],
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=self._prompts.step3_subcompetencies,
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": self._task_payload(task, tags),
                        "competency": {
                            "id": str(competency.id),
                            "name": competency.name,
                            "description": competency.description,
                        },
                        "available_subcompetencies": [
                            {
                                "llm_id": index,
                                "id": str(sub.id),
                                "name": sub.name,
                                "description": sub.description,
                                "weight": sub.weight,
                            }
                            for index, sub in enumerate(
                                competency.sub_competencies, start=1
                            )
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _category_messages(
        self,
        task: Task,
        categories: list[Category],
        tags: list[str],
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=self._prompts.step1_categories,
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": self._task_payload(task, tags),
                        "available_categories": [
                            {
                                "llm_id": index,
                                "id": str(category.id),
                                "name": category.name,
                                "description": category.description,
                            }
                            for index, category in enumerate(categories, start=1)
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _task_payload(self, task: Task, tags: list[str]) -> dict[str, object]:
        return {
            "external_id": task.external_id,
            "title": task.title,
            "description": task.description,
            "type": task.type.value,
            "tags": tags,
        }

    def _resolve_ids(
        self,
        selected: list[TaskCategorySelectionDTO]
        | list[TaskCompetencySelectionDTO]
        | list[TaskSubCompetencySelectionDTO],
        entities: list[Category] | list[Competency] | list[SubCompetency],
    ) -> set[UUID]:
        resolved: set[UUID] = set()
        for item in selected:
            resolved_id = self._resolve_single_id(item.id, item.llm_id, entities)
            if resolved_id is not None:
                resolved.add(resolved_id)
        return resolved

    def _resolve_single_id(
        self,
        direct_id: UUID | None,
        llm_id: int | None,
        entities: list[Category] | list[Competency] | list[SubCompetency],
    ) -> UUID | None:
        if direct_id is not None:
            return direct_id
        if llm_id is None or llm_id <= 0 or llm_id > len(entities):
            return None
        return entities[llm_id - 1].id

    def _normalize_mappings(
        self,
        response: TaskSubCompetencyExtractionResultDTO,
        subcompetencies: list[SubCompetency],
    ) -> list[TaskCompetencyMapping]:
        allowed_ids = {subcompetency.id for subcompetency in subcompetencies}
        merged_weights: dict[UUID, float] = defaultdict(float)

        for mapping in response.sub_competencies:
            resolved_id = mapping.id
            if resolved_id is None or resolved_id not in allowed_ids:
                continue
            weight = max(0.0, min(1.0, float(mapping.weight)))
            if weight <= 0.0:
                continue
            merged_weights[resolved_id] += weight

        ranked = sorted(
            merged_weights.items(),
            key=lambda item: (-item[1], str(item[0])),
        )[: self._max_mappings]
        total = sum(weight for _, weight in ranked)
        if total <= 0.0:
            return []

        return [
            TaskCompetencyMapping(
                sub_competency_id=sub_competency_id,
                weight=weight / total,
            )
            for sub_competency_id, weight in ranked
        ]


class SyncTasksUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        gateway: ExternalTestingSystemGateway,
        llm_gateway: LLMGateway,
        job_queue: LLMJobQueuePort,
        *,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
        prompt_version: str = "v1",
    ) -> None:
        self._uow = uow
        self._gateway = gateway
        self._mapper = MapTaskToCompetenciesUseCase(
            llm_gateway,
            max_parallel_requests=max_parallel_requests,
            stage_timeout_seconds=stage_timeout_seconds,
            prompt_version=prompt_version,
        )
        self._job_queue = job_queue

    async def execute(self) -> SyncTasksResultDTO:
        external_tasks = await self._gateway.list_tasks()

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
                    )
                else:
                    task.title = record.title
                    task.description = record.description
                    task.type = record.type

                task.competency_mappings = []
                task.mapping_status = TaskMappingStatus.PENDING
                task.mapping_error_message = None
                task.mapping_validated = False
                await uow.tasks.add(task)
                synced.append(_task_to_dto(task))

            await uow.commit()
        for record in external_tasks:
            await self._enqueue_mapping(record.external_id, tags=record.tags)
        return SyncTasksResultDTO(synced_tasks=synced)

    async def _enqueue_mapping(
        self,
        task_external_id: str,
        *,
        tags: list[str],
    ) -> None:
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.TASK_MAPPING,
            payload={"task_external_id": task_external_id},
            runner=lambda: self._process_mapping(task_external_id, tags=tags),
        )

    async def _process_mapping(self, task_external_id: str, *, tags: list[str]) -> None:
        async with self._uow as uow:
            task = await uow.tasks.get_by_external_id(
                task_external_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                return
            categories = await uow.categories.get_list(
                include={CategoryInclude.SUB_COMPETENCIES}
            )
            try:
                task.competency_mappings = await self._mapper.execute(
                    task,
                    list(categories),
                    tags=tags,
                )
                task.mapping_status = TaskMappingStatus.COMPLETED
                task.mapping_error_message = None
            except Exception as exc:
                task.competency_mappings = []
                task.mapping_status = TaskMappingStatus.FAILED
                task.mapping_error_message = str(exc)
            task.mapping_validated = False
            await uow.tasks.add(task)
            await uow.commit()


class RebuildTaskMappingUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        llm_gateway: LLMGateway,
        job_queue: LLMJobQueuePort,
        *,
        max_parallel_requests: int = 4,
        stage_timeout_seconds: float = 45.0,
        prompt_version: str = "v1",
    ) -> None:
        self._uow = uow
        self._mapper = MapTaskToCompetenciesUseCase(
            llm_gateway,
            max_parallel_requests=max_parallel_requests,
            stage_timeout_seconds=stage_timeout_seconds,
            prompt_version=prompt_version,
        )
        self._job_queue = job_queue

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(
                task_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            task.mapping_status = TaskMappingStatus.PENDING
            task.mapping_error_message = None
            task.mapping_validated = False
            await uow.tasks.add(task)
            await uow.commit()
            dto = _task_to_dto(task)

        await self._enqueue_mapping(task.external_id, tags=[])
        return dto

    async def _enqueue_mapping(
        self,
        task_external_id: str,
        *,
        tags: list[str],
    ) -> None:
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.TASK_MAPPING,
            payload={"task_external_id": task_external_id},
            runner=lambda: self._process_mapping(task_external_id, tags=tags),
        )

    async def _process_mapping(self, task_external_id: str, *, tags: list[str]) -> None:
        async with self._uow as uow:
            task = await uow.tasks.get_by_external_id(
                task_external_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                return
            categories = await uow.categories.get_list(
                include={CategoryInclude.SUB_COMPETENCIES}
            )
            try:
                task.competency_mappings = await self._mapper.execute(
                    task,
                    list(categories),
                    tags=tags,
                )
                task.mapping_status = TaskMappingStatus.COMPLETED
                task.mapping_error_message = None
            except Exception as exc:
                task.competency_mappings = []
                task.mapping_status = TaskMappingStatus.FAILED
                task.mapping_error_message = str(exc)
            task.mapping_validated = False
            await uow.tasks.add(task)
            await uow.commit()


class ValidateTaskMappingUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(
                task_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            task.mapping_validated = True
            await uow.tasks.add(task)
            await uow.commit()
            return _task_to_dto(task)


class ListTasksUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[TaskDTO]:
        async with self._uow as uow:
            tasks = await uow.tasks.get_list(
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS}
            )
            return [_task_to_dto(task) for task in tasks]


class GetTaskUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(
                task_id,
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
            )
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            return _task_to_dto(task)
