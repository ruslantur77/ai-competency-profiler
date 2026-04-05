from __future__ import annotations

import logging
from uuid import UUID, uuid4

from competency_system.application.dtos.mappers import task_dto_from_domain
from competency_system.application.dtos.task import (
    SyncTasksResultDTO,
    TaskDTO,
)
from competency_system.application.llm.llm_dispatch_payload import (
    TaskExtractionPayload,
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
    TaskSubCompetencyMapping,
)
from competency_system.domain.value_objects.enums import TaskMappingStatus

logger = logging.getLogger(__name__)


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
                    include={TaskInclude.SUB_COMPETENCY_MAPPINGS},
                )
                if not task:
                    # TODO: Use NotFoundException
                    raise ValueError(f"Task {task_id} not found")
                categories = await uow.categories.get_list()

            task.sub_competency_mappings = await self._map(task, list(categories))
            task.mapping_status = TaskMappingStatus.COMPLETED
            task.mapping_error_message = None
            logger.info(
                "llm_operation_finished",
                extra={
                    "operation": "map_task_to_competencies",
                    "status": "success",
                    "task_id": str(task_id),
                    "mappings_count": len(task.sub_competency_mappings),
                    "mappings_sample": [
                        {
                            "sub_competency_id": str(item.sub_competency_id),
                            "weight": item.weight,
                        }
                        for item in task.sub_competency_mappings[:3]
                    ],
                },
            )
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
            task.sub_competency_mappings = []
            task.mapping_status = TaskMappingStatus.FAILED
            task.mapping_error_message = str(exc)
        task.mapping_validated = False
        async with self._uow as uow:
            await uow.tasks.add(task)
            await uow.commit()

    async def _map(
        self,
        task: Task,
        categories: list[Category],
    ) -> list[TaskSubCompetencyMapping]:
        if not categories:
            return []

        subcompetencies, _ = await self.llm_pipeline.execute(
            categories=categories,
            competencies_by_category=self.competencies_by_category,
            sub_competencies_by_competency=self.sub_competencies_by_competency,
            payload=self._task_payload(task),
        )

        return self._normalize_mappings(task.id, subcompetencies)

    def _task_payload(self, task: Task) -> dict[str, object]:
        return {
            "title": task.title,
            "description": task.description,
        }

    def _normalize_mappings(
        self,
        task_id: UUID,
        subcompetencies: list[SubCompetency],
    ) -> list[TaskSubCompetencyMapping]:
        ranked = sorted(subcompetencies, key=lambda item: item.weight)[
            : self._max_mappings
        ]

        return [
            TaskSubCompetencyMapping(
                sub_competency_id=sub_competency.id,
                sub_competency=sub_competency,
                weight=sub_competency.weight,
                position=idx,
                task_id=task_id,
            )
            for idx, sub_competency in enumerate(ranked)
        ]


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

                task.sub_competency_mappings = []
                task.mapping_status = TaskMappingStatus.PENDING
                task.mapping_error_message = None
                task.mapping_validated = False
                await uow.tasks.add(task)
                await self._enqueue_mapping(task.id)
                synced.append(task_dto_from_domain(task))
                await uow.commit()

        return SyncTasksResultDTO(synced_tasks=synced)

    async def _enqueue_mapping(self, task_id: UUID) -> None:
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.TASK_MAPPING,
            payload=TaskExtractionPayload(task_id=task_id, raw_text="").model_dump(
                mode="json"
            ),
        )


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
        self._mapper = MapTaskToCompetenciesOperation(
            llm_gateway,
            uow=uow,
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
            dto = task_dto_from_domain(task)

        await self._enqueue_mapping(task.id)
        return dto

    async def _enqueue_mapping(self, task_id: UUID) -> None:
        await self._job_queue.enqueue(
            # TODO: replace in-process runner with external queue producer.
            job_type=LLMJobType.TASK_MAPPING,
            payload=TaskExtractionPayload(task_id=task_id, raw_text="").model_dump(
                mode="json"
            ),
        )


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
            return task_dto_from_domain(task)


class ListTasksUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[TaskDTO]:
        async with self._uow as uow:
            tasks = await uow.tasks.get_list(
                include={TaskInclude.SUB_COMPETENCY_MAPPINGS}
            )
            return [task_dto_from_domain(task) for task in tasks]


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
            return task_dto_from_domain(task)
