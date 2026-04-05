from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from competency_system.application.id_mapper import IDMapper
from competency_system.application.llm_orchestrator import (
    LLMCallSpec,
    StructuredLLMOrchestrator,
)
from competency_system.application.ports.llm import LLMMessage
from competency_system.domain.entities import (
    Category,
    Competency,
    SubCompetency,
    VacancyGraphSuggestion,
)
from competency_system.domain.value_objects import (
    CompetencyLevel,
    SuggestionEntityType,
    SuggestionStage,
)

logger = logging.getLogger(__name__)


class LLMSelectionCategoriesOutput(BaseModel):
    categories: list[int]
    categories_uuid: list[UUID] = Field(default_factory=list)


class LLMSelectionCompetenciesOutput(BaseModel):
    class _SuggestedItem(BaseModel):
        name: str
        description: str
        is_required: bool
        weight: float
        reason: str

    competencies: list[int]
    competencies_uuid: list[UUID] = Field(default_factory=list)
    suggested_new: list[_SuggestedItem] = Field(default_factory=list)


class LLMSelectionSubCompetenciesOutput(BaseModel):
    class _SuggestedItem(BaseModel):
        name: str
        description: str
        target_level: int
        weight: float
        reason: str

    class _SubCompetencyItem(BaseModel):
        id: UUID | None = None
        llm_id: int | None = None
        target_level: int
        weight: float

        @model_validator(mode="after")
        def _validate_identity_fields(
            self,
        ) -> LLMSelectionSubCompetenciesOutput._SubCompetencyItem:
            if self.id is None and self.llm_id is None:
                raise ValueError("Either 'id' or 'llm_id' must be provided")
            if self.id is not None and self.llm_id is not None:
                raise ValueError("Only one of 'id' or 'llm_id' can be provided")
            return self

    sub_competencies: list[_SubCompetencyItem]
    suggested_new: list[_SuggestedItem] = Field(default_factory=list)


@dataclass
class StageConfig[TResponse: BaseModel]:
    system_prompt: str
    response_model: type[TResponse]
    temperature: float = 0.1


@dataclass
class PipelineConfig[
    R1: BaseModel,
    R2: BaseModel,
    R3: BaseModel,
]:
    stage1: StageConfig[R1]
    stage2: StageConfig[R2]
    stage3: StageConfig[R3]

    category_to_dict: Callable[[Any], dict[str, Any]]
    competency_to_dict: Callable[[Any], dict[str, Any]]
    sub_competency_to_dict: Callable[[Any], dict[str, Any]]


class ThreeStagePipeline[
    R1: LLMSelectionCategoriesOutput,
    R2: LLMSelectionCompetenciesOutput,
    R3: LLMSelectionSubCompetenciesOutput,
]:
    # TODO: добавить ограничения по количеству элементов

    def __init__(
        self,
        orchestrator: StructuredLLMOrchestrator,
        config: PipelineConfig[R1, R2, R3],
    ) -> None:
        self._orchestrator = orchestrator
        self._cfg = config

    async def execute(
        self,
        categories: Sequence[Category],
        competencies_by_category: Callable[[UUID], Awaitable[list[Competency]]],
        sub_competencies_by_competency: Callable[
            [UUID], Awaitable[list[SubCompetency]]
        ],
        payload: dict[str, Any],
    ) -> tuple[list[SubCompetency], list[VacancyGraphSuggestion]]:

        selected_categories = await self._stage1(categories, payload)
        if not selected_categories[0]:
            return [], []

        selected_competencies, _, comp_suggestions = await self._stage2(
            competencies_by_category, selected_categories[0], payload
        )
        if not selected_competencies:
            return [], comp_suggestions

        sub_competencies, _, sub_suggestions = await self._stage3(
            sub_competencies_by_competency, selected_competencies, payload
        )

        suggestions = comp_suggestions + sub_suggestions
        return sub_competencies, suggestions

    async def _stage1(
        self, categories: Sequence[Category], payload: dict[str, Any]
    ) -> tuple[list[Category], LLMSelectionCategoriesOutput]:
        cat_mapper = IDMapper(categories)
        category_ids = {item.id for item in categories}
        response = await self._orchestrator.run(
            LLMCallSpec[LLMSelectionCategoriesOutput](
                stage="stage1_categories",
                messages=self._make_messages(
                    self._cfg.stage1.system_prompt,
                    {
                        "task": payload,
                        "available_categories": cat_mapper.to_prompt_items(
                            self._cfg.category_to_dict
                        ),
                    },
                ),
                response_model=self._cfg.stage1.response_model,
                temperature=self._cfg.stage1.temperature,
            )
        )
        selected_category_ids = set(cat_mapper.get_item_ids([*response.categories]))
        selected_category_ids.update(
            category_id
            for category_id in response.categories_uuid
            if category_id in category_ids
        )
        for llm_id in response.categories:
            if cat_mapper.get_item_id(llm_id) is None:
                logger.warning(
                    "pipeline_invalid_reference",
                    extra={
                        "stage": "stage1_categories",
                        "kind": "category_llm_id",
                        "raw_id": llm_id,
                    },
                )
        for category_id in response.categories_uuid:
            if category_id not in category_ids:
                logger.warning(
                    "pipeline_invalid_reference",
                    extra={
                        "stage": "stage1_categories",
                        "kind": "category_uuid",
                        "raw_id": str(category_id),
                    },
                )
        selected_categories = [c for c in categories if c.id in selected_category_ids]
        return selected_categories, response

    async def _stage2(
        self,
        competencies_by_category: Callable[[UUID], Awaitable[list[Competency]]],
        selected_categories: list[Category],
        payload: dict[str, Any],
    ) -> tuple[
        list[Competency],
        list[LLMSelectionCompetenciesOutput],
        list[VacancyGraphSuggestion],
    ]:
        comp_mapper_by_cat: dict[UUID, IDMapper] = {}
        specs: list[LLMCallSpec[LLMSelectionCompetenciesOutput]] = []
        comp_by_cat: dict[UUID, list[Competency]] = {}
        cats_with_specs: list[Category] = []

        for cat in selected_categories:
            comps = await competencies_by_category(cat.id)
            comp_by_cat[cat.id] = comps
            if not comps:
                continue
            mapper = IDMapper(comps)
            comp_mapper_by_cat[cat.id] = mapper
            cats_with_specs.append(cat)
            specs.append(
                LLMCallSpec[LLMSelectionCompetenciesOutput](
                    stage="stage2_competencies",
                    messages=self._make_messages(
                        self._cfg.stage2.system_prompt,
                        {
                            "task": payload,
                            "category": self._cfg.category_to_dict(cat),
                            "available_competencies": mapper.to_prompt_items(
                                self._cfg.competency_to_dict
                            ),
                        },
                    ),
                    response_model=self._cfg.stage2.response_model,
                    temperature=self._cfg.stage2.temperature,
                )
            )

        if not specs:
            return [], [], []

        responses = await self._orchestrator.run_many(specs)
        if len(responses) != len(specs):
            raise RuntimeError(
                "Stage2 response/spec mismatch: "
                f"{len(responses)} responses for {len(specs)} specs"
            )
        selected_competencies: list[Competency] = []
        suggestions: list[VacancyGraphSuggestion] = []

        for cat, response_c in zip(cats_with_specs, responses, strict=True):
            mapper = comp_mapper_by_cat[cat.id]
            known_competency_ids = {item.id for item in comp_by_cat[cat.id]}
            resolved = set(mapper.get_item_ids([*response_c.competencies]))
            resolved.update(
                competency_id
                for competency_id in response_c.competencies_uuid
                if competency_id in known_competency_ids
            )

            for llm_id in response_c.competencies:
                if mapper.get_item_id(llm_id) is None:
                    logger.warning(
                        "pipeline_invalid_reference",
                        extra={
                            "stage": "stage2_competencies",
                            "kind": "competency_llm_id",
                            "raw_id": llm_id,
                        },
                    )
            for competency_id in response_c.competencies_uuid:
                if competency_id not in known_competency_ids:
                    logger.warning(
                        "pipeline_invalid_reference",
                        extra={
                            "stage": "stage2_competencies",
                            "kind": "competency_uuid",
                            "raw_id": str(competency_id),
                        },
                    )
            selected_competencies.extend(
                c for c in comp_by_cat[cat.id] if c.id in resolved
            )
            for item in response_c.suggested_new:
                suggestions.append(
                    VacancyGraphSuggestion(
                        id=uuid4(),
                        vacancy_id=UUID(int=0),
                        stage=SuggestionStage.COMPETENCY,
                        entity_type=SuggestionEntityType.COMPETENCY,
                        name=item.name,
                        description=item.description,
                        reason=item.reason,
                        is_required=item.is_required,
                        weight=item.weight,
                        parent_category_id=cat.id,
                    )
                )

        return selected_competencies, responses, suggestions

    async def _stage3(
        self,
        sub_competencies_by_competency: Callable[
            [UUID], Awaitable[list[SubCompetency]]
        ],
        selected_competencies: list[Competency],
        payload: dict[str, Any],
    ) -> tuple[
        list[SubCompetency],
        list[LLMSelectionSubCompetenciesOutput],
        list[VacancyGraphSuggestion],
    ]:
        sub_mapper_by_comp: dict[UUID, IDMapper] = {}
        specs: list[LLMCallSpec[LLMSelectionSubCompetenciesOutput]] = []
        sub_by_comp: dict[UUID, list[SubCompetency]] = {}
        comps_with_specs: list[Competency] = []

        for comp in selected_competencies:
            subs = await sub_competencies_by_competency(comp.id)
            sub_by_comp[comp.id] = subs
            if not subs:
                continue
            mapper = IDMapper(subs)
            sub_mapper_by_comp[comp.id] = mapper
            comps_with_specs.append(comp)
            specs.append(
                LLMCallSpec[LLMSelectionSubCompetenciesOutput](
                    stage="stage3_subcompetencies",
                    messages=self._make_messages(
                        self._cfg.stage3.system_prompt,
                        {
                            "task": payload,
                            "competency": self._cfg.competency_to_dict(comp),
                            "available_subcompetencies": mapper.to_prompt_items(
                                self._cfg.sub_competency_to_dict
                            ),
                        },
                    ),
                    response_model=self._cfg.stage3.response_model,
                    temperature=self._cfg.stage3.temperature,
                )
            )

        if not specs:
            return [], [], []

        responses = await self._orchestrator.run_many(specs)
        if len(responses) != len(specs):
            raise RuntimeError(
                "Stage3 response/spec mismatch: "
                f"{len(responses)} responses for {len(specs)} specs"
            )
        selected_sub_competencies: list[SubCompetency] = []
        suggestions: list[VacancyGraphSuggestion] = []

        for comp, response in zip(comps_with_specs, responses, strict=True):
            mapper = sub_mapper_by_comp[comp.id]
            sub_by_id = {item.id: item for item in sub_by_comp[comp.id]}
            selected_for_comp: dict[UUID, SubCompetency] = {}

            for item in response.sub_competencies:
                sub_id = item.id
                if sub_id is None:
                    if item.llm_id is None:
                        logger.warning(
                            "pipeline_invalid_reference",
                            extra={
                                "stage": "stage3_subcompetencies",
                                "kind": "sub_competency_llm_id",
                                "raw_id": None,
                            },
                        )
                        continue
                    sub_id = mapper.get_item_id(item.llm_id)
                    if sub_id is None:
                        logger.warning(
                            "pipeline_invalid_reference",
                            extra={
                                "stage": "stage3_subcompetencies",
                                "kind": "sub_competency_llm_id",
                                "raw_id": item.llm_id,
                            },
                        )
                        continue
                if sub_id not in sub_by_id:
                    logger.warning(
                        "pipeline_invalid_reference",
                        extra={
                            "stage": "stage3_subcompetencies",
                            "kind": "sub_competency_uuid",
                            "raw_id": str(sub_id),
                        },
                    )
                    continue
                try:
                    target_level = CompetencyLevel(item.target_level)
                except ValueError:
                    logger.warning(
                        "pipeline_invalid_reference",
                        extra={
                            "stage": "stage3_subcompetencies",
                            "kind": "target_level",
                            "raw_id": item.target_level,
                        },
                    )
                    continue
                source = sub_by_id[sub_id]
                selected_for_comp[sub_id] = SubCompetency(
                    id=source.id,
                    competency_id=source.competency_id,
                    name=source.name,
                    description=source.description,
                    weight=item.weight,
                    target_level=target_level,
                    competency=source.competency,
                )
            selected_sub_competencies.extend(selected_for_comp.values())
            for item_new in response.suggested_new:
                suggestions.append(
                    VacancyGraphSuggestion(
                        id=uuid4(),
                        vacancy_id=UUID(int=0),
                        stage=SuggestionStage.SUB_COMPETENCY,
                        entity_type=SuggestionEntityType.SUB_COMPETENCY,
                        name=item_new.name,
                        description=item_new.description,
                        reason=item_new.reason,
                        target_level=CompetencyLevel(item.target_level),
                        weight=item.weight,
                        parent_competency_id=comp.id,
                    )
                )

        return selected_sub_competencies, responses, suggestions

    @staticmethod
    def _make_messages(
        system_prompt: str, user_payload: dict[str, Any]
    ) -> list[LLMMessage]:
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(
                role="user",
                content=json.dumps(user_payload, ensure_ascii=False, indent=2),
            ),
        ]
