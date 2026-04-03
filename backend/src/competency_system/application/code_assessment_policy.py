from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeAssessmentPolicy:
    version: str
    criteria: tuple[str, ...]

    @property
    def system_prompt(self) -> str:
        criteria_text = "\n".join(f"- {criterion}" for criterion in self.criteria)
        return (
            "Assess the submitted code against the task requirements. "
            "Return JSON with fields: passed, score, feedback, feedback_items.\n"
            "feedback_items must be an array of objects: "
            "{type: 'positive'|'negative', value: string, position: integer}.\n"
            "Use these fixed criteria:\n"
            f"{criteria_text}\n"
            "Score range must be 0..100."
        )


DEFAULT_CODE_ASSESSMENT_POLICY = CodeAssessmentPolicy(
    version="v1",
    criteria=(
        "Correctness against task intent and provided tests",
        "Code quality and readability",
        "Algorithmic and structural efficiency",
        "Reliability and edge-case handling",
    ),
)
