from __future__ import annotations

import logging

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
from competency_system.domain.value_objects import CompetencyLevel, SuggestionStage

pytestmark = pytest.mark.unit


class _Orchestrator:
    def __init__(self, stage1_response, run_many_responses) -> None:  # type: ignore[no-untyped-def]
        self._stage1_response = stage1_response
        self._run_many_responses = list(run_many_responses)

    async def run(self, spec):  # type: ignore[no-untyped-def]
        return self._stage1_response

    async def run_many(self, specs):  # type: ignore[no-untyped-def]
        return self._run_many_responses[: len(specs)]


class _MismatchedOrchestrator(_Orchestrator):
    async def run_many(self, specs):  # type: ignore[no-untyped-def]
        return self._run_many_responses


def _config() -> PipelineConfig:
    return PipelineConfig(
        stage1=StageConfig(
            system_prompt="s1", response_model=LLMSelectionCategoriesOutput
        ),
        stage2=StageConfig(
            system_prompt="s2",
            response_model=LLMSelectionCompetenciesOutput,
        ),
        stage3=StageConfig(
            system_prompt="s3",
            response_model=LLMSelectionSubCompetenciesOutput,
        ),
        category_to_dict=lambda category: {"name": category.name},
        competency_to_dict=lambda competency: {"name": competency.name},
        sub_competency_to_dict=lambda sub: {"name": sub.name},
    )


def _graph() -> tuple[Category, Competency, SubCompetency]:
    category = Category(name="Backend")
    competency = Competency(category_id=category.id, name="Python")
    sub = SubCompetency(
        competency_id=competency.id,
        name="AsyncIO",
        description="event loop",
        weight=0.3,
    )
    competency.sub_competencies = [sub]
    category.competencies = [competency]
    return category, competency, sub


async def test_pipeline_stage1_selects_by_llm_id() -> None:
    category, _, _ = _graph()
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [],
        ),
        config=_config(),
    )

    selected, _ = await pipeline._stage1([category], {"task": "x"})

    assert [item.id for item in selected] == [category.id]


async def test_pipeline_stage1_selects_by_uuid() -> None:
    category, _, _ = _graph()
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[], categories_uuid=[category.id]),
            [],
        ),
        config=_config(),
    )

    selected, _ = await pipeline._stage1([category], {"task": "x"})

    assert [item.id for item in selected] == [category.id]


async def test_pipeline_execute_keeps_stage2_suggestions_without_selected_competencies() -> (
    None
):
    category, competency, _ = _graph()
    stage2 = LLMSelectionCompetenciesOutput(
        competencies=[],
        suggested_new=[
            LLMSelectionCompetenciesOutput._SuggestedItem(
                name="Caching",
                description="cache",
                is_required=True,
                weight=0.5,
                reason="needed",
            )
        ],
    )
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [stage2],
        ),
        config=_config(),
    )

    async def _comps(_category_id):
        return [competency]

    async def _subs(_comp_id):
        return []

    selected_subs, suggestions = await pipeline.execute(
        [category],
        competencies_by_category=_comps,
        sub_competencies_by_competency=_subs,
        payload={"task": "x"},
    )

    assert selected_subs == []
    assert len(suggestions) == 1
    assert suggestions[0].stage == SuggestionStage.COMPETENCY


async def test_pipeline_stage2_uses_competency_uuid_selection() -> None:
    category, competency, _ = _graph()
    stage2 = LLMSelectionCompetenciesOutput(
        competencies=[],
        competencies_uuid=[competency.id],
        suggested_new=[],
    )
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [stage2],
        ),
        config=_config(),
    )

    async def _comps(_category_id):
        return [competency]

    selected_competencies, _, _ = await pipeline._stage2(
        _comps, [category], {"task": "x"}
    )

    assert [item.id for item in selected_competencies] == [competency.id]


async def test_pipeline_stage3_selects_by_sub_uuid_and_applies_weight_and_level() -> (
    None
):
    _, competency, sub = _graph()
    stage3 = LLMSelectionSubCompetenciesOutput(
        sub_competencies=[
            LLMSelectionSubCompetenciesOutput._SubCompetencyItem(
                id=sub.id,
                target_level=4,
                weight=0.9,
            )
        ],
        suggested_new=[],
    )
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [stage3],
        ),
        config=_config(),
    )

    async def _subs(_competency_id):
        return [sub]

    selected_subs, _, _ = await pipeline._stage3(_subs, [competency], {"task": "x"})

    assert len(selected_subs) == 1
    assert selected_subs[0].id == sub.id
    assert selected_subs[0].weight == 0.9
    assert selected_subs[0].target_level == CompetencyLevel.ADVANCED


async def test_pipeline_stage2_raises_on_response_spec_mismatch() -> None:
    category, competency, _ = _graph()
    pipeline = ThreeStagePipeline(
        orchestrator=_MismatchedOrchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [],
        ),
        config=_config(),
    )

    async def _comps(_category_id):
        return [competency]

    with pytest.raises(RuntimeError, match="Stage2 response/spec mismatch"):
        await pipeline._stage2(_comps, [category], {"task": "x"})


async def test_pipeline_stage3_raises_on_response_spec_mismatch() -> None:
    _, competency, sub = _graph()
    pipeline = ThreeStagePipeline(
        orchestrator=_MismatchedOrchestrator(
            LLMSelectionCategoriesOutput(categories=[1]),
            [],
        ),
        config=_config(),
    )

    async def _subs(_competency_id):
        return [sub]

    with pytest.raises(RuntimeError, match="Stage3 response/spec mismatch"):
        await pipeline._stage3(_subs, [competency], {"task": "x"})


async def test_pipeline_logs_and_ignores_invalid_references(
    caplog: pytest.LogCaptureFixture,
) -> None:
    category, competency, sub = _graph()
    stage2 = LLMSelectionCompetenciesOutput(
        competencies=[999],
        suggested_new=[],
    )
    stage3 = LLMSelectionSubCompetenciesOutput(
        sub_competencies=[
            LLMSelectionSubCompetenciesOutput._SubCompetencyItem(
                llm_id=999,
                target_level=3,
                weight=1.0,
            )
        ],
        suggested_new=[],
    )
    pipeline = ThreeStagePipeline(
        orchestrator=_Orchestrator(
            LLMSelectionCategoriesOutput(categories=[1, 999]),
            [stage2, stage3],
        ),
        config=_config(),
    )

    async def _comps(_category_id):
        return [competency]

    async def _subs(_competency_id):
        return [sub]

    with caplog.at_level(logging.WARNING):
        selected_subs, suggestions = await pipeline.execute(
            [category],
            competencies_by_category=_comps,
            sub_competencies_by_competency=_subs,
            payload={"task": "x"},
        )

    assert selected_subs == []
    assert suggestions == []
    assert "pipeline_invalid_reference" in caplog.text
