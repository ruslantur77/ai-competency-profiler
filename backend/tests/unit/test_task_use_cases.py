from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from competency_system.application.ports.external_testing_system import (
    ExternalTaskRecord,
    ExternalTestingSystemGateway,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.task import (
    MapTaskToCompetenciesOperation,
    SyncTasksUseCase,
)
from competency_system.domain.entities import Category, Competency, SubCompetency, Task
from competency_system.domain.value_objects.enums import TaskMappingStatus, TaskType

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xfail(reason="Legacy use-case tests pending rewrite"),
]


class FakeLLMGateway(LLMGateway):
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.calls: list[list[LLMMessage]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> BaseModel:
        self.calls.append(messages)
        if not self.responses:
            raise RuntimeError("No fake responses left")
        return response_model.model_validate(self.responses.pop(0))


class FakeTestingGateway(ExternalTestingSystemGateway):
    def __init__(self, tasks: list[ExternalTaskRecord]) -> None:
        self._tasks = tasks

    async def list_tasks(self) -> list[ExternalTaskRecord]:
        return self._tasks


@pytest.mark.asyncio
async def test_map_task_to_competencies_normalizes_response() -> None:
    sub1 = SubCompetency(name="Parsing JSON")
    sub2 = SubCompetency(name="Working with SQL")
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Parse and store data",
        type=TaskType.CODE,
    )
    category = Category(
        name="Backend",
        description="Backend systems",
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="APIs",
                description="API design and implementation",
                sub_competencies=[sub1, sub2],
            )
        ],
    )
    category.competencies[0].category_id = category.id
    fake_llm = FakeLLMGateway(
        [
            {"categories": [{"llm_id": 1}]},
            {"competencies": [{"llm_id": 1}]},
            {
                "sub_competencies": [
                    {"llm_id": 1, "weight": 0.2},
                    {"llm_id": 1, "weight": 0.3},
                    {"llm_id": 2, "weight": 0.5},
                    {"id": str(uuid4()), "weight": 1.0},
                ]
            },
        ]
    )

    use_case = MapTaskToCompetenciesOperation(fake_llm)
    mappings = await use_case._map(task, [category], tags=["api", "sql"])

    assert len(mappings) == 2
    assert {mapping.sub_competency_id for mapping in mappings} == {sub1.id, sub2.id}
    assert sum(mapping.weight for mapping in mappings) == pytest.approx(1.0)
    assert next(
        mapping.weight for mapping in mappings if mapping.sub_competency_id == sub1.id
    ) == pytest.approx(0.5)
    assert next(
        mapping.weight for mapping in mappings if mapping.sub_competency_id == sub2.id
    ) == pytest.approx(0.5)
    assert "api" in fake_llm.calls[0][1].content


@pytest.mark.asyncio
async def test_map_task_to_competencies_rejects_invalid_schema() -> None:
    sub1 = SubCompetency(name="Parsing JSON")
    category = Category(
        name="Backend",
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="APIs",
                sub_competencies=[sub1],
            )
        ],
    )
    category.competencies[0].category_id = category.id
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Parse and store data",
        type=TaskType.CODE,
    )
    fake_llm = FakeLLMGateway([{}])
    use_case = MapTaskToCompetenciesOperation(fake_llm)

    with pytest.raises(ValidationError):
        await use_case._map(task, [category], tags=[])


@pytest.mark.asyncio
async def test_sync_tasks_use_case_marks_task_completed_without_sqlite(
    mock_uow,
) -> None:
    gateway = FakeTestingGateway(
        [
            ExternalTaskRecord(
                external_id="task-sync-1",
                title="API task",
                description="Build and persist data",
                type=TaskType.CODE,
                tags=["json", "sql"],
            )
        ]
    )
    fake_llm = FakeLLMGateway([])
    mock_uow.categories.list.return_value = []
    mock_uow.tasks.get_by_external_id.return_value = None

    result = await SyncTasksUseCase(mock_uow, gateway, fake_llm).execute()

    assert len(result.synced_tasks) == 1
    assert result.synced_tasks[0].external_id == "task-sync-1"
    assert result.synced_tasks[0].mapping_status == TaskMappingStatus.COMPLETED
    assert result.synced_tasks[0].mapping_validated is False
    mock_uow.tasks.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()
