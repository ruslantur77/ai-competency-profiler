# ruff: noqa: E501
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
                "You select relevant competency categories for an IT vacancy.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level key: categories (list of integer IDs from available_categories).\n"
                "Only include IDs that are relevant to the vacancy. Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Requirements: Python, PostgreSQL, REST API design.",\n'
                '  "available_categories": [\n'
                '    {"id": 1, "name": "Programming Languages"},\n'
                '    {"id": 2, "name": "Databases"},\n'
                '    {"id": 3, "name": "Soft Skills"},\n'
                '    {"id": 4, "name": "Mobile Development"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                '{"categories": [1, 2, 3]}'
            ),
            step2_competencies=(
                "You select relevant competencies within a given category for an IT vacancy.\n"
                "You may also propose new competencies that are important but missing from the list.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level keys:\n"
                "  - competencies: list of integer IDs from available_competencies\n"
                "  - suggested_new: list of new competency objects with fields: "
                "name, description, is_required (bool), weight (0..1), reason\n"
                "Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Requirements: Python, PostgreSQL, REST API design.",\n'
                '  "category": {"id": 1, "name": "Programming Languages"},\n'
                '  "available_competencies": [\n'
                '    {"id": 1, "name": "Python", "description": "Core Python knowledge"},\n'
                '    {"id": 2, "name": "Java", "description": "Java development"},\n'
                '    {"id": 3, "name": "Go", "description": "Go language"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                "{\n"
                '  "competencies": [1],\n'
                '  "suggested_new": [\n'
                "    {\n"
                '      "name": "Async Python",\n'
                '      "description": "Knowledge of asyncio and async frameworks",\n'
                '      "is_required": false,\n'
                '      "weight": 0.6,\n'
                '      "reason": "Async Python is common in modern backend services but not listed"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
            step3_subcompetencies=(
                "You select relevant subcompetencies within a given competency for an IT vacancy.\n"
                "You may also propose new subcompetencies that are important but missing from the list.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level keys:\n"
                "  - sub_competencies: list of objects with fields: llm_id (int), "
                "target_level (0..5), weight (0..1)\n"
                "  - suggested_new: list of new subcompetency objects with fields: "
                "name, description, target_level (0..5), weight (0..1), reason\n"
                "Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Requirements: Python, PostgreSQL, REST API design.",\n'
                '  "competency": {"id": 1, "name": "Python"},\n'
                '  "available_sub_competencies": [\n'
                '    {"id": 1, "name": "OOP", "description": "Object-oriented design in Python"},\n'
                '    {"id": 2, "name": "Testing", "description": "pytest, unit and integration tests"},\n'
                '    {"id": 3, "name": "Type hints", "description": "Usage of typing module"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                "{\n"
                '  "sub_competencies": [\n'
                '    {"llm_id": 1, "target_level": 4, "weight": 0.5},\n'
                '    {"llm_id": 2, "target_level": 3, "weight": 0.3}\n'
                "  ],\n"
                '  "suggested_new": [\n'
                "    {\n"
                '      "name": "Async/Await",\n'
                '      "description": "Writing async code with asyncio",\n'
                '      "target_level": 3,\n'
                '      "weight": 0.2,\n'
                '      "reason": "Async patterns are expected at senior level but not listed"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
        )
    }

    _TASK_PROMPTS: dict[str, ThreeStagePrompts] = {
        "v1": ThreeStagePrompts(
            step1_categories=(
                "You select relevant competency categories for an assessment task.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level key: categories (list of integer IDs from available_categories).\n"
                "Only include IDs that are relevant to the task. Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Implement a REST endpoint in Python that accepts a list of integers and returns their sorted order.",\n'
                '  "available_categories": [\n'
                '    {"id": 1, "name": "Programming Languages"},\n'
                '    {"id": 2, "name": "Algorithms & Data Structures"},\n'
                '    {"id": 3, "name": "Databases"},\n'
                '    {"id": 4, "name": "Mobile Development"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                '{"categories": [1, 2]}'
            ),
            step2_competencies=(
                "You select relevant competencies within a given category for an assessment task.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level key: competencies (list of integer IDs from available_competencies).\n"
                "Do not propose new competencies. Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Implement a REST endpoint in Python that accepts a list of integers and returns their sorted order.",\n'
                '  "category": {"id": 1, "name": "Programming Languages"},\n'
                '  "available_competencies": [\n'
                '    {"id": 1, "name": "Python", "description": "Core Python knowledge"},\n'
                '    {"id": 2, "name": "Java", "description": "Java development"},\n'
                '    {"id": 3, "name": "Go", "description": "Go language"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                '{"competencies": [1]}'
            ),
            step3_subcompetencies=(
                "You select relevant subcompetencies within a given competency for an assessment task.\n"
                "Output MUST be a single JSON object and nothing else — no markdown, no explanation.\n"
                "Allowed top-level key: sub_competencies (list of objects with fields: "
                "llm_id (int), weight (0..1)).\n"
                "Do not propose new subcompetencies. Do not add extra keys.\n\n"
                "Example input:\n"
                "{\n"
                '  "task": "Implement a REST endpoint in Python that accepts a list of integers and returns their sorted order.",\n'
                '  "competency": {"id": 1, "name": "Python"},\n'
                '  "available_sub_competencies": [\n'
                '    {"id": 1, "name": "OOP", "description": "Object-oriented design in Python"},\n'
                '    {"id": 2, "name": "Testing", "description": "pytest, unit and integration tests"},\n'
                '    {"id": 3, "name": "Type hints", "description": "Usage of typing module"}\n'
                "  ]\n"
                "}\n\n"
                "Example output:\n"
                "{\n"
                '  "sub_competencies": [\n'
                '    {"llm_id": 1, "weight": 0.4},\n'
                '    {"llm_id": 3, "weight": 0.6}\n'
                "  ]\n"
                "}"
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
