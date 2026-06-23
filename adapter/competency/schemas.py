from typing import Optional

from pydantic import BaseModel


class CandidateTaskAssessmentDTO(BaseModel):
    """DTO для отправки в наш webhook POST /webhook/task-completed"""

    event_id: str
    vacancy_id: str
    candidate_external_id: str
    task_external_id: str
    type: str  # "code" | "test"
    code: Optional[str] = None
    question_answers: list[dict] = []
    passed: int = 0
    total: int = 0
    attempts: int = 1
    duration_seconds: int = 0