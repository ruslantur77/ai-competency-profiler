from __future__ import annotations

import pytest

from competency_system.application.llm.prompts import PromptCatalog


@pytest.mark.unit
def test_prompt_catalog_returns_task_and_vacancy_versions() -> None:
    catalog = PromptCatalog()

    vacancy = catalog.get_vacancy_prompts("v1")
    task = catalog.get_task_prompts("v1")
    code = catalog.get_code_assessment_prompts("v1")

    assert "преимущественно русский" in vacancy.step2_competencies.lower()
    assert "общепринятые техтермины" in vacancy.step3_subcompetencies.lower()
    assert "оценочного задания" in task.step1_categories.lower()
    assert vacancy.step1_categories != task.step1_categories
    assert "feedback и feedback_items[].value" in code.prompt
    assert "преимущественно на русском" in code.prompt.lower()


@pytest.mark.unit
def test_prompt_catalog_rejects_unknown_version() -> None:
    catalog = PromptCatalog()

    with pytest.raises(ValueError):
        catalog.get_vacancy_prompts("v999")
    with pytest.raises(ValueError):
        catalog.get_task_prompts("v999")
    with pytest.raises(ValueError):
        catalog.get_code_assessment_prompts("v999")
