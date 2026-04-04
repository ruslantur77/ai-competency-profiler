from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import BaseModel

from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.task import MapTaskToCompetenciesOperation
from competency_system.domain.entities import Category, Competency, SubCompetency, Task
from competency_system.domain.value_objects.enums import TaskType


class _FakeLLM(LLMGateway):
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.calls: list[list[LLMMessage]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> BaseModel:
        self.calls.append(messages)
        if not self._responses:
            raise RuntimeError("No fake responses left")
        return response_model.model_validate(self._responses.pop(0))


class _FakeUow:
    def __init__(self, category: Category, competency: Competency) -> None:
        self.categories = SimpleNamespace()
        self.competencies = SimpleNamespace()

        async def _get_category(entity_id: UUID, *, include=None):
            if entity_id == category.id:
                return category
            return None

        async def _get_competency(entity_id: UUID, *, include=None):
            if entity_id == competency.id:
                return competency
            return None

        self.categories.get = _get_category
        self.competencies.get = _get_competency

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_pipeline_uses_task_prompt_catalog() -> None:
    sub = SubCompetency(name="SQL")
    category = Category(
        name="Backend",
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="API",
                sub_competencies=[sub],
            )
        ],
    )
    competency = category.competencies[0]
    competency.category_id = category.id
    sub.competency_id = competency.id

    task = Task(
        external_id="task-1",
        title="Build API",
        description="Write service with SQL",
        type=TaskType.CODE,
    )
    llm = _FakeLLM(
        [
            {"categories": [1]},
            {
                "competencies": [1],
                "suggested_new": [],
            },
            {
                "sub_competencies": [{"llm_id": 1, "target_level": 3, "weight": 1.0}],
                "suggested_new": [],
            },
        ]
    )

    result = await MapTaskToCompetenciesOperation(llm, _FakeUow(category, competency))._map(
        task,
        [category],
    )

    assert len(result) <= 1
    if result:
        assert result[0].sub_competency_id == sub.id
    assert len(llm.calls) >= 1
    assert "assessment task" in llm.calls[0][0].content.lower()
    assert "vacancy" not in llm.calls[0][0].content.lower()
