from __future__ import annotations

from uuid import UUID

from competency_system.application.dtos.base import BaseDTO
from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.dtos.vacancy import VacancyCreateDTO


class VacancyExtractionPayloadDTO(VacancyCreateDTO):
    """Payload for the vacancy extraction DAG."""

    prompt_version: str | None = None


class TaskSyncPayloadDTO(BaseDTO):
    prompt_version: str | None = None


class CandidateAssessmentTriggerDTO(CandidateTaskAssessmentDTO):
    pass


class RankingRecalculationTriggerDTO(BaseDTO):
    vacancy_id: UUID
