from __future__ import annotations

import pytest

from competency_system.application.llm.prompts import PromptCatalog


@pytest.mark.unit
def test_prompt_catalog_returns_task_and_vacancy_versions() -> None:
    catalog = PromptCatalog()

    vacancy = catalog.get_vacancy_prompts("v1")
    task = catalog.get_task_prompts("v1")

    assert "vacancy" in vacancy.step1_categories.lower()
    assert "assessment task" in task.step1_categories.lower()
    assert vacancy.step1_categories != task.step1_categories


@pytest.mark.unit
def test_prompt_catalog_rejects_unknown_version() -> None:
    catalog = PromptCatalog()

    with pytest.raises(ValueError):
        catalog.get_vacancy_prompts("v999")
    with pytest.raises(ValueError):
        catalog.get_task_prompts("v999")
