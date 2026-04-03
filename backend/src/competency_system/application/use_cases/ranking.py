from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from competency_system.application.dtos.ranking import (
    RankingBreakdownItemDTO,
    RankingItemDTO,
    VacancyRankingDTO,
)
from competency_system.application.dtos.webhooks import (
    RankingSnapshot,
    RankingSnapshotPayload,
)
from competency_system.application.ports.repositories import (
    CandidateInclude,
    VacancyInclude,
)
from competency_system.application.ports.uow import UnitOfWork
from competency_system.domain.services.ranking_engine import RankingEngine


class RecalculateRankingUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._ranking_engine = RankingEngine()

    async def execute(self, vacancy_id: UUID) -> VacancyRankingDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(
                vacancy_id,
                include={VacancyInclude.NORMALIZED_GRAPH},
            )
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")

            candidates = await uow.candidates.list_by_vacancy(
                vacancy_id,
                include={CandidateInclude.ACHIEVEMENTS},
            )
            ranking_scores = self._ranking_engine.rank_candidates(
                vacancy, list(candidates)
            )
            dto = VacancyRankingDTO(
                vacancy_id=vacancy_id,
                rankings=[
                    RankingItemDTO(
                        candidate_id=item.candidate_id,
                        candidate_external_id=item.candidate_external_id,
                        total_score=item.total_score,
                        required_match=item.required_match,
                        desired_match=item.desired_match,
                        required_score=item.required_score,
                        desired_score=item.desired_score,
                        breakdown=[
                            RankingBreakdownItemDTO(
                                competency_id=breakdown.competency_id,
                                competency_name=breakdown.competency_name,
                                required=breakdown.required,
                                matched_weight=breakdown.matched_weight,
                                total_weight=breakdown.total_weight,
                                coverage=breakdown.coverage,
                                score_contribution=breakdown.score_contribution,
                                matched_subcompetency_ids=list(
                                    breakdown.matched_subcompetency_ids
                                ),
                                total_subcompetency_ids=list(
                                    breakdown.total_subcompetency_ids
                                ),
                            )
                            for breakdown in item.breakdown
                        ],
                    )
                    for item in ranking_scores
                ],
            )
            snapshot = await uow.ranking_snapshots.get_by_vacancy(vacancy_id)
            now = datetime.now(UTC)
            if snapshot is None:
                snapshot = RankingSnapshot(
                    id=uuid4(),
                    vacancy_id=vacancy_id,
                    payload=RankingSnapshotPayload(data=dto.model_dump(mode="json")),
                    calculated_at=now,
                    created_at=now,
                )
            else:
                snapshot.payload = RankingSnapshotPayload(
                    data=dto.model_dump(mode="json")
                )
                snapshot.calculated_at = now
            await uow.ranking_snapshots.add(snapshot)
            await uow.commit()
            return dto


class GetVacancyRankingUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._recalculate = RecalculateRankingUseCase(uow)

    async def execute(self, vacancy_id: UUID) -> VacancyRankingDTO:
        async with self._uow as uow:
            vacancy = await uow.vacancies.get(vacancy_id)
            if vacancy is None:
                raise ValueError(f"Vacancy {vacancy_id} not found")
            snapshot = await uow.ranking_snapshots.get_by_vacancy(vacancy_id)
            if snapshot is not None:
                return VacancyRankingDTO.model_validate(snapshot.payload.data)
        return await self._recalculate.execute(vacancy_id)
