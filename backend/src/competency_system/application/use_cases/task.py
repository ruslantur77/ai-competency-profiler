from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
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
from competency_system.application.ports.uow import UnitOfWork
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
        max_mappings: int = 8,
    ) -> None:
        self._llm = llm_gateway
        self._max_mappings = max_mappings

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
        response = await self._llm.generate(
            [
                LLMMessage(
                    role="system",
                    content=(
                        "Select matching competency categories for a testing task. "
                        "Return JSON with key 'categories'. "
                        "Each item must include llm_id from provided options."
                    ),
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
            ],
            TaskCategoryExtractionResultDTO,
            temperature=0.1,
        )
        selected_ids = self._resolve_ids(response.categories, categories)
        return [category for category in categories if category.id in selected_ids]

    async def _select_competencies(
        self,
        task: Task,
        categories: list[Category],
        tags: list[str],
    ) -> list[Competency]:
        selected: list[Competency] = []
        for category in categories:
            if not category.competencies:
                continue
            response = await self._llm.generate(
                self._competency_messages(task, category, tags),
                TaskCompetencyExtractionResultDTO,
                temperature=0.1,
            )
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
        payload: list[TaskCompetencyMappingDTO] = []
        for competency in competencies:
            if not competency.sub_competencies:
                continue
            response = await self._llm.generate(
                self._subcompetency_messages(task, competency, tags),
                TaskSubCompetencyExtractionResultDTO,
                temperature=0.1,
            )
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
                content=(
                    "Select matching competencies within a category "
                    "for a testing task. "
                    "Return JSON with key 'competencies'. "
                    "Each item must include llm_id from provided options."
                ),
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
                content=(
                    "Select matching subcompetencies for a testing task. "
                    "Return JSON with key 'sub_competencies'. "
                    "Each item must include llm_id and weight in range [0,1]."
                ),
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
                                "target_level": int(sub.target_level),
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
    ) -> None:
        self._uow = uow
        self._gateway = gateway
        self._mapper = MapTaskToCompetenciesUseCase(llm_gateway)

    async def execute(self) -> SyncTasksResultDTO:
        external_tasks = await self._gateway.list_tasks()

        async with self._uow as uow:
            categories = await uow.categories.list()
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

                try:
                    task.competency_mappings = await self._build_mappings(
                        task,
                        categories,
                        tags=record.tags,
                    )
                    task.mapping_status = TaskMappingStatus.COMPLETED
                    task.mapping_error_message = None
                except Exception as exc:
                    task.competency_mappings = []
                    task.mapping_status = TaskMappingStatus.FAILED
                    task.mapping_error_message = str(exc)
                task.mapping_validated = False
                await uow.tasks.add(task)
                synced.append(_task_to_dto(task))

            await uow.commit()
            return SyncTasksResultDTO(synced_tasks=synced)

    async def _build_mappings(
        self,
        task: Task,
        categories: Sequence[Category],
        *,
        tags: list[str],
    ) -> list[TaskCompetencyMapping]:
        return await self._mapper.execute(task, list(categories), tags=tags)


class RebuildTaskMappingUseCase:
    def __init__(self, uow: UnitOfWork, llm_gateway: LLMGateway) -> None:
        self._uow = uow
        self._mapper = MapTaskToCompetenciesUseCase(llm_gateway)

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            categories = await uow.categories.list()
            task.competency_mappings = await self._mapper.execute(
                task,
                list(categories),
                tags=[],
            )
            task.mapping_status = TaskMappingStatus.COMPLETED
            task.mapping_error_message = None
            task.mapping_validated = False
            await uow.tasks.add(task)
            await uow.commit()
            return _task_to_dto(task)


class ValidateTaskMappingUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
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
            tasks = await uow.tasks.list()
            return [_task_to_dto(task) for task in tasks]


class GetTaskUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            return _task_to_dto(task)
