from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThreeStagePrompts:
    step1_categories: str
    step2_competencies: str
    step3_subcompetencies: str


@dataclass(frozen=True)
class LLMCodeAssessmentPrompts:
    prompt: str


class PromptCatalog:
    # TODO: move prompt storage and version management to DB.
    _VACANCY_PROMPTS: dict[str, ThreeStagePrompts] = {
        "v1": ThreeStagePrompts(
            step1_categories=(
                "You extract existing competency categories for an IT vacancy.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level key: categories.\n"
                "Each item in categories must reference exactly one existing "
                "category using one field: llm_id.\n"
                "Do not propose new categories. Do not add extra keys."
            ),
            step2_competencies=(
                "You extract competencies inside one category for an IT vacancy.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level keys: competencies, suggested_new.\n"
                "For competencies: each item references exactly one existing "
                "competency using one field: llm_id.\n"
                "For suggested_new: omit id/llm_id and provide name, description, "
                "is_required, weight (0..1), reason.\n"
                "Do not add extra keys."
            ),
            step3_subcompetencies=(
                "You extract subcompetencies inside one competency for an IT vacancy.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level keys: sub_competencies, suggested_new.\n"
                "For sub_competencies: each item references exactly one existing "
                "subcompetency using one field: llm_id, and includes target_level "
                "(0..5) and weight (0..1).\n"
                "For suggested_new: omit id/llm_id and provide name, description, "
                "target_level (0..5), weight (0..1), reason.\n"
                "Do not add extra keys."
            ),
        )
    }

    _TASK_PROMPTS: dict[str, ThreeStagePrompts] = {
        "v1": ThreeStagePrompts(
            step1_categories=(
                "You extract existing competency categories for an assessment task.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level key: categories.\n"
                "Each item in categories must reference exactly one existing "
                "category using one field: llm_id.\n"
                "Do not add extra keys."
            ),
            step2_competencies=(
                "You extract existing competencies inside one category for an "
                "assessment task.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level key: competencies.\n"
                "Each item in competencies must reference exactly one existing "
                "competency using one field: llm_id.\n"
                "Do not add extra keys."
            ),
            step3_subcompetencies=(
                "You extract existing subcompetencies inside one competency for an "
                "assessment task.\n"
                "Output MUST be a single JSON object and nothing else.\n"
                "Allowed top-level key: sub_competencies.\n"
                "Each item in sub_competencies must reference exactly one existing "
                "subcompetency using one field: llm_id and include weight in range "
                "[0, 1].\n"
                "Do not add extra keys."
            ),
        )
    }

    _CODE_ASSESSMENT_PROMPTS: dict[str, LLMCodeAssessmentPrompts] = {
        "v1": LLMCodeAssessmentPrompts(
            prompt=(
                "Assess the submitted code against the task requirements. "
                "Return JSON with fields: passed, score, feedback, feedback_items.\n"
                "feedback_items must be an array of objects: "
                "{type: 'positive'|'negative', value: string, position: integer}.\n"
                "Use these fixed criteria:\n"
                "- Correctness against task intent and provided tests\n"
                "- Code quality and readability\n"
                "- Algorithmic and structural efficiency\n"
                "- Reliability and edge-case handling\n"
                "- Score range must be 0..100."
            )
        )
    }

    def get_vacancy_prompts(self, version: str) -> ThreeStagePrompts:
        prompts = self._VACANCY_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown vacancy prompt version: {version}")
        return prompts

    def get_task_prompts(self, version: str) -> ThreeStagePrompts:
        prompts = self._TASK_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown task prompt version: {version}")
        return prompts

    def get_code_assessment_prompts(self, version: str) -> LLMCodeAssessmentPrompts:
        prompts = self._CODE_ASSESSMENT_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown code assessment prompt version: {version}")
        return prompts
