from __future__ import annotations

from uuid import UUID

from competency_system.application.dtos.base import BaseDTO


class RankingBreakdownItemDTO(BaseDTO):
    competency_id: UUID
    competency_name: str
    required: bool
    matched_weight: float
    total_weight: float
    coverage: float
    score_contribution: float
    matched_subcompetency_ids: list[UUID]
    total_subcompetency_ids: list[UUID]


class RankingItemDTO(BaseDTO):
    candidate_id: UUID
    candidate_external_id: str
    total_score: float
    required_match: float
    desired_match: float
    required_score: float
    desired_score: float
    breakdown: list[RankingBreakdownItemDTO]


class VacancyRankingDTO(BaseDTO):
    vacancy_id: UUID
    rankings: list[RankingItemDTO]
