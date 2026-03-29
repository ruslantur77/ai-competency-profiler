from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID, uuid4

from competency_system.application.dtos.task import (
    SyncTasksResultDTO,
    TaskCompetencyMappingDTO,
    TaskDTO,
    TaskMappingExtractionResultDTO,
)
from competency_system.application.ports.external_testing_system import (
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.entities import (
    SubCompetency,
    Task,
    TaskCompetencyMapping,
)


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
        subcompetencies: list[SubCompetency],
        *,
        tags: list[str] | None = None,
    ) -> list[TaskCompetencyMapping]:
        if not subcompetencies:
            return []

        response = await self._llm.generate(
            self._build_messages(task, subcompetencies, tags=tags or []),
            TaskMappingExtractionResultDTO,
            temperature=0.1,
        )
        return self._normalize_mappings(response, subcompetencies)

    def _build_messages(
        self,
        task: Task,
        subcompetencies: list[SubCompetency],
        *,
        tags: list[str],
    ) -> list[LLMMessage]:
        return [
            LLMMessage(
                role="system",
                content=(
                    "You map testing tasks to existing subcompetencies. "
                    "Return JSON only with key 'mappings'. "
                    "Each mapping must contain sub_competency_id and weight. "
                    "Only use subcompetency IDs from the provided list."
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": {
                            "external_id": task.external_id,
                            "title": task.title,
                            "description": task.description,
                            "type": task.type.value,
                            "tags": tags,
                        },
                        "available_subcompetencies": [
                            {
                                "id": str(subcompetency.id),
                                "name": subcompetency.name,
                                "description": subcompetency.description,
                                "target_level": int(subcompetency.target_level),
                                "weight": subcompetency.weight,
                            }
                            for subcompetency in subcompetencies
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        ]

    def _normalize_mappings(
        self,
        response: TaskMappingExtractionResultDTO,
        subcompetencies: list[SubCompetency],
    ) -> list[TaskCompetencyMapping]:
        allowed_ids = {subcompetency.id for subcompetency in subcompetencies}
        merged_weights: dict[UUID, float] = defaultdict(float)

        for mapping in response.mappings:
            if mapping.sub_competency_id not in allowed_ids:
                continue
            weight = max(0.0, min(1.0, float(mapping.weight)))
            if weight <= 0.0:
                continue
            merged_weights[mapping.sub_competency_id] += weight

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
            subcompetencies = await uow.sub_competencies.list()
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

                task.competency_mappings = await self._build_mappings(
                    task,
                    subcompetencies,
                    tags=record.tags,
                )
                task.mapping_validated = False
                await uow.tasks.add(task)
                synced.append(_task_to_dto(task))

            await uow.commit()
            return SyncTasksResultDTO(synced_tasks=synced)

    async def _build_mappings(
        self,
        task: Task,
        subcompetencies: Sequence[SubCompetency],
        *,
        tags: list[str],
    ) -> list[TaskCompetencyMapping]:
        try:
            return await self._mapper.execute(task, list(subcompetencies), tags=tags)
        except Exception:
            return []


class RebuildTaskMappingUseCase:
    def __init__(self, uow: UnitOfWork, llm_gateway: LLMGateway) -> None:
        self._uow = uow
        self._mapper = MapTaskToCompetenciesUseCase(llm_gateway)

    async def execute(self, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            subcompetencies = await uow.sub_competencies.list()
            task.competency_mappings = await self._mapper.execute(
                task,
                list(subcompetencies),
                tags=[],
            )
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
