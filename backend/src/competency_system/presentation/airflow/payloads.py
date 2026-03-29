from __future__ import annotations

from uuid import UUID

from competency_system.application.dtos.base import BaseDTO
from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.dtos.vacancy import VacancyCreateDTO


class VacancyExtractionPayloadDTO(VacancyCreateDTO):
    """Payload for the vacancy extraction DAG."""


class CandidateAssessmentTriggerDTO(CandidateTaskAssessmentDTO):
    vacancy_id: UUID | None = None


class RankingRecalculationTriggerDTO(BaseDTO):
    vacancy_id: UUID
