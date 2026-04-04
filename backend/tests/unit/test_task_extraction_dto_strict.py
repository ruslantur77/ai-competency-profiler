from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from competency_system.application.dtos.task import (
    TaskCategoryExtractionResultDTO,
    TaskSubCompetencyExtractionResultDTO,
)


@pytest.mark.unit
def test_task_category_extraction_forbids_extra_keys() -> None:
    with pytest.raises(ValidationError):
        TaskCategoryExtractionResultDTO.model_validate(
            {
                "categories": [{"llm_id": 1}],
                "unexpected": [],
            }
        )


@pytest.mark.unit
def test_task_subcompetency_selection_rejects_both_id_and_llm_id() -> None:
    with pytest.raises(ValidationError):
        TaskSubCompetencyExtractionResultDTO.model_validate(
            {
                "sub_competencies": [
                    {"id": str(uuid4()), "llm_id": 1, "weight": 0.8},
                ]
            }
        )


@pytest.mark.unit
def test_task_subcompetency_selection_rejects_weight_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TaskSubCompetencyExtractionResultDTO.model_validate(
            {
                "sub_competencies": [
                    {"llm_id": 1, "weight": 1.5},
                ]
            }
        )
