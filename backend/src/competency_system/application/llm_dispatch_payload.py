from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CodeAssessmentPayload(BaseModel):
    test_result_id: UUID
    passed_tests: int
    total_tests: int
    duration_seconds: int


class TaskExtractionPayload(BaseModel):
    task_id: UUID
    raw_text: str


class VacancyExtractionPayload(BaseModel):
    vacancy_id: UUID
    raw_text: str
