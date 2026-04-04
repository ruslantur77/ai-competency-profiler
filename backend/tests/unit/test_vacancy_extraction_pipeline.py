from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from competency_system.application.dtos.vacancy import (
    VacancyCategoryExtractionResultDTO,
    VacancyCompetencyExtractionResultDTO,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.vacancy import ExtractVacancyGraphUseCase
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import SuggestionStage


class _FakeLLMGateway(LLMGateway):
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)

    async def generate(
        self,
        messages: list[LLMMessage],
        response_model: type[BaseModel],
        *,
        temperature: float = 0.2,
    ) -> BaseModel:
        if not self._responses:
            raise RuntimeError("No fake responses left")
        return response_model.model_validate(self._responses.pop(0))


def _catalog_fixture() -> list[Category]:
    category = Category(id=uuid4(), name="Backend", description="Backend systems")
    competency = Competency(
        id=uuid4(),
        category_id=category.id,
        name="Python",
        description="Python programming",
    )
    sub1 = SubCompetency(
        id=uuid4(),
        competency_id=competency.id,
        name="AsyncIO",
        description="Async IO primitives",
        weight=0.4,
    )
    sub2 = SubCompetency(
        id=uuid4(),
        competency_id=competency.id,
        name="Typing",
        description="Type hints and mypy",
        weight=0.6,
    )
    competency.sub_competencies = [sub1, sub2]
    category.competencies = [competency]
    return [category]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_graph_uses_target_levels_from_step3(mock_uow) -> None:
    catalog = _catalog_fixture()
    use_case = ExtractVacancyGraphUseCase(
        mock_uow,
        _FakeLLMGateway(
            [
                {"categories": [{"llm_id": 1}]},
                {"competencies": [{"llm_id": 1, "weight": 1.0}], "suggested_new": []},
                {
                    "sub_competencies": [
                        {"llm_id": 1, "target_level": 4, "weight": 0.7},
                        {"llm_id": 2, "target_level": 2, "weight": 0.3},
                    ],
                    "suggested_new": [],
                },
            ]
        ),
        SimpleNamespace(),
    )

    graph = await use_case._build_graph(
        Vacancy(name="Senior Python", description="High-load backend"),
        catalog,
    )

    levels_by_sub: dict[UUID, CompetencyLevel] = {
        node.sub_competency_id: node.target_level for node in graph.sub_competency_nodes
    }
    assert len(levels_by_sub) == 2
    assert levels_by_sub[catalog[0].competencies[0].sub_competencies[0].id] == 4
    assert levels_by_sub[catalog[0].competencies[0].sub_competencies[1].id] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_graph_caps_only_suggested_new(mock_uow) -> None:
    catalog = _catalog_fixture()
    many_new_comp = [
        {
            "name": f"new-comp-{index}",
            "weight": 0.1,
            "is_required": True,
            "reason": "gap",
        }
        for index in range(10)
    ]
    many_new_sub = [
        {
            "name": f"new-sub-{index}",
            "target_level": 3,
            "weight": 0.1,
            "reason": "gap",
        }
        for index in range(10)
    ]
    use_case = ExtractVacancyGraphUseCase(
        mock_uow,
        _FakeLLMGateway(
            [
                {"categories": [{"llm_id": 1}]},
                {
                    "competencies": [{"llm_id": 1, "weight": 1.0}],
                    "suggested_new": many_new_comp,
                },
                {
                    "sub_competencies": [
                        {"llm_id": 1, "target_level": 3, "weight": 1.0}
                    ],
                    "suggested_new": many_new_sub,
                },
            ]
        ),
        SimpleNamespace(),
        max_suggested_new_per_stage=5,
    )

    graph = await use_case._build_graph(
        Vacancy(name="Python vacancy", description="Backend"),
        catalog,
    )

    competency_suggestions = [
        item for item in graph.suggestions if item.stage == SuggestionStage.COMPETENCY
    ]
    sub_suggestions = [
        item
        for item in graph.suggestions
        if item.stage == SuggestionStage.SUB_COMPETENCY
    ]
    assert len(competency_suggestions) == 5
    assert len(sub_suggestions) == 5


@pytest.mark.unit
def test_category_extraction_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        VacancyCategoryExtractionResultDTO.model_validate(
            {
                "categories": [{"llm_id": 1}],
                "suggested_new": [],
            }
        )


@pytest.mark.unit
def test_competency_extraction_rejects_invalid_selected_item() -> None:
    with pytest.raises(ValidationError):
        VacancyCompetencyExtractionResultDTO.model_validate(
            {
                "competencies": [{"id": str(uuid4()), "llm_id": 1}],
                "suggested_new": [],
            }
        )
