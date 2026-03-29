from __future__ import annotations

from typing import Protocol

from competency_system.domain.entities import Candidate, Vacancy
from competency_system.domain.services.ranking_engine import RankingScore


class RankingEnginePort(Protocol):
    def rank_candidates(
        self,
        vacancy: Vacancy,
        candidates: list[Candidate],
    ) -> list[RankingScore]: ...
