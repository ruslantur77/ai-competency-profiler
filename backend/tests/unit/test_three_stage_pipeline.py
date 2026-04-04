from __future__ import annotations

import pytest

from competency_system.application.pipeline import (
    LLMSelectionCategoriesOutput,
    LLMSelectionCompetenciesOutput,
    LLMSelectionSubCompetenciesOutput,
    PipelineConfig,
    StageConfig,
    ThreeStagePipeline,
)
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.domain.value_objects.enums import SuggestionStage

pytestmark = pytest.mark.unit


class _Orchestrator:
    def __init__(self, stage1_response, stage_many_responses) -> None:  # type: ignore[no-untyped-def]
        self._stage1_response = stage1_response
        self._stage_many_responses = list(stage_many_responses)

    async def run(self, spec):  # type: ignore[no-untyped-def]
        return self._stage1_response

    async def run_many(self, specs):  # type: ignore[no-untyped-def]
        return self._stage_many_responses[: len(specs)]


def _config() -> PipelineConfig:
    return PipelineConfig(
        stage1=StageConfig(system_prompt="s1", response_model=LLMSelectionCategoriesOutput),
        stage2=StageConfig(
            system_prompt="s2", response_model=LLMSelectionCompetenciesOutput
        ),
        stage3=StageConfig(
            system_prompt="s3", response_model=LLMSelectionSubCompetenciesOutput
        ),
        category_to_dict=lambda category: {"name": category.name},
        competency_to_dict=lambda competency: {"name": competency.name},
        sub_competency_to_dict=lambda sub: {"name": sub.name},
    )


async def test_three_stage_pipeline_returns_empty_when_no_categories_selected() -> None:
    category = Category(name="Backend")
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[]),
            [],
        ),
        config=_config(),
    )

    async def _no_competencies(_category_id):
        return []

    async def _no_subs(_comp_id):
        return []

    selected, suggestions = await pipeline.execute(
        [category],
        competencies_by_category=_no_competencies,
        sub_competencies_by_competency=_no_subs,
        payload={"task": "x"},
    )

    assert selected == []
    assert suggestions == []


async def test_three_stage_pipeline_returns_empty_when_stage2_has_no_specs() -> None:
    category = Category(name="Backend")
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [],
        ),
        config=_config(),
    )

    async def _no_competencies(_category_id):
        return []

    async def _no_subs(_comp_id):
        return []

    selected, suggestions = await pipeline.execute(
        [category],
        competencies_by_category=_no_competencies,
        sub_competencies_by_competency=_no_subs,
        payload={"task": "x"},
    )

    assert selected == []
    assert suggestions == []


async def test_three_stage_pipeline_builds_selected_subs_and_suggestions() -> None:
    category = Category(name="Backend")
    competency = Competency(category_id=category.id, name="Python")
    sub = SubCompetency(competency_id=competency.id, name="AsyncIO", weight=0.3)
    competency.sub_competencies = [sub]
    category.competencies = [competency]
    stage2 = LLMSelectionCompetenciesOutput(
        competencies=[1],
        suggested_new=[
            LLMSelectionCompetenciesOutput._SuggestedItem(
                name="Caching",
                description="desc",
                is_required=True,
                weight=0.5,
                reason="needed",
            )
        ],
    )
    stage3 = LLMSelectionSubCompetenciesOutput(
        sub_competencies=[
            LLMSelectionSubCompetenciesOutput._SubCompetencyItem(
                llm_id=1,
                target_level=3,
                weight=0.7,
            )
        ],
        suggested_new=[
            LLMSelectionSubCompetenciesOutput._SuggestedItem(
                name="FastAPI",
                description="desc",
                target_level=4,
                weight=0.4,
                reason="api",
            )
        ],
    )
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [stage2, stage3],
        ),
        config=_config(),
    )

    async def _comps(_category_id):
        return [competency]

    async def _subs(_competency_id):
        return [sub]

    selected, suggestions = await pipeline.execute(
        [category],
        competencies_by_category=_comps,
        sub_competencies_by_competency=_subs,
        payload={"task": "x"},
    )

    assert [item.id for item in selected] == [sub.id]
    assert {item.stage for item in suggestions} == {
        SuggestionStage.COMPETENCY,
        SuggestionStage.SUB_COMPETENCY,
    }
