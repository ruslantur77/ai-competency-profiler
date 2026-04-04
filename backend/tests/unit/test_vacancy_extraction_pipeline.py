from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

import competency_system.domain.entities as domain_entities
from competency_system.application.dtos.vacancy import (
    VacancyCategoryExtractionResultDTO,
    VacancyCompetencyExtractionResultDTO,
)
from competency_system.application.ports.llm import LLMGateway, LLMMessage
from competency_system.application.use_cases.vacancy import (
    ExtractVacancyGraphOperation,
    _VacancyGraphPayload,
)
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
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


class _FakeUow:
    def __init__(self, categories: list[Category]) -> None:
        self.categories = SimpleNamespace()
        self.competencies = SimpleNamespace()
        by_category = {item.id: item for item in categories}
        by_competency = {
            comp.id: comp for cat in categories for comp in cat.competencies
        }

        async def _get_category(entity_id: UUID, *, include=None):
            return by_category.get(entity_id)

        async def _get_competency(entity_id: UUID, *, include=None):
            return by_competency.get(entity_id)

        self.categories.get = _get_category
        self.competencies.get = _get_competency

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


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
async def test_extract_graph_map_returns_empty_for_empty_catalog() -> None:
    _VacancyGraphPayload.model_rebuild(_types_namespace=vars(domain_entities))
    op = ExtractVacancyGraphOperation(
        _FakeUow([]),
        _FakeLLMGateway([]),
    )

    graph = await op._map(Vacancy(name="Senior Python", description="Backend"), [])

    assert graph.categories == []
    assert graph.competencies == []
    assert graph.category_nodes == []
    assert graph.competency_nodes == []
    assert graph.sub_competency_nodes == []
    assert graph.suggestions == []


@pytest.mark.unit
async def test_extract_graph_map_builds_nodes_and_suggestions() -> None:
    _VacancyGraphPayload.model_rebuild(_types_namespace=vars(domain_entities))
    catalog = _catalog_fixture()
    op = ExtractVacancyGraphOperation(
        _FakeUow(catalog),
        _FakeLLMGateway(
            [
                {"categories": [1], "categories_uuid": []},
                {
                    "competencies": [1],
                    "competencies_uuid": [],
                    "suggested_new": [
                        {
                            "name": "Caching",
                            "description": "Cache strategy",
                            "is_required": True,
                            "weight": 0.4,
                            "reason": "core",
                        }
                    ],
                },
                {
                    "sub_competencies": [
                        {"llm_id": 1, "target_level": 4, "weight": 0.7},
                        {"llm_id": 2, "target_level": 2, "weight": 0.3},
                    ],
                    "suggested_new": [
                        {
                            "name": "FastAPI",
                            "description": "framework",
                            "target_level": 3,
                            "weight": 0.5,
                            "reason": "api",
                        }
                    ],
                },
            ]
        ),
    )

    graph = await op._map(
        Vacancy(name="Senior Python", description="High-load backend"),
        catalog,
    )

    assert len(graph.categories) == 1
    assert isinstance(graph.category_nodes, list)
    assert isinstance(graph.competency_nodes, list)
    assert isinstance(graph.sub_competency_nodes, list)
    assert isinstance(graph.suggestions, list)
    if graph.suggestions:
        assert {item.stage for item in graph.suggestions} <= {
            SuggestionStage.COMPETENCY,
            SuggestionStage.SUB_COMPETENCY,
        }


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
