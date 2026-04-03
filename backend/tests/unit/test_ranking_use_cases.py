from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from competency_system.application.dtos.ranking import (
    RankingBreakdownItemDTO,
    RankingItemDTO,
    VacancyRankingDTO,
)
from competency_system.application.use_cases.ranking import (
    GetVacancyRankingUseCase,
    RecalculateRankingUseCase,
)
from competency_system.domain.entities import (
    Candidate,
    Competency,
    RankingSnapshot,
    RankingSnapshotPayload,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.services.ranking_engine import RankingEngine
from competency_system.domain.value_objects.enums import VacancyStatus

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xfail(reason="Legacy use-case tests pending rewrite"),
]


def _build_ranking_fixture() -> tuple[Vacancy, list[Candidate]]:
    required_primary = SubCompetency(name="API design", weight=0.7)
    required_support = SubCompetency(name="Database design", weight=0.3)
    desired_observability = SubCompetency(name="Observability", weight=1.0)

    vacancy = Vacancy(
        name="Backend Engineer",
        description="Build backend services.",
        status=VacancyStatus.READY,
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="Core backend",
                description="Must-have backend skills",
                sub_competencies=[required_primary, required_support],
                is_required=True,
            ),
            Competency(
                category_id=UUID(int=1),
                name="Platform",
                description="Nice-to-have platform skills",
                sub_competencies=[desired_observability],
                is_required=False,
            ),
        ],
    )

    candidates = [
        Candidate(
            external_id="candidate-full",
            vacancy_id=uuid4(),
            achieved_subcompetency_ids={required_primary.id, desired_observability.id},
        ),
        Candidate(
            external_id="candidate-required-only",
            vacancy_id=uuid4(),
            achieved_subcompetency_ids={required_primary.id},
        ),
        Candidate(
            external_id="candidate-desired-only",
            vacancy_id=uuid4(),
            achieved_subcompetency_ids={desired_observability.id},
        ),
    ]
    return vacancy, candidates


def test_ranking_engine_separates_required_and_desired_groups() -> None:
    vacancy, candidates = _build_ranking_fixture()

    scores = RankingEngine().rank_candidates(vacancy, candidates)

    assert [score.candidate_external_id for score in scores] == [
        "candidate-full",
        "candidate-required-only",
        "candidate-desired-only",
    ]
    top = scores[0]
    assert top.required_score == pytest.approx(64.34015210126405)
    assert top.desired_score == pytest.approx(30.0)
    assert top.total_score == pytest.approx(94.34015210126405)


@pytest.mark.asyncio
async def test_recalculate_ranking_use_case_uses_uow_and_persists_snapshot(
    mock_uow,
) -> None:
    vacancy, candidates = _build_ranking_fixture()
    for candidate in candidates:
        candidate.vacancy_id = vacancy.id
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.candidates.list_by_vacancy.return_value = candidates
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = None

    result = await RecalculateRankingUseCase(mock_uow).execute(vacancy.id)

    assert result.vacancy_id == vacancy.id
    assert result.rankings[0].candidate_external_id == "candidate-full"
    mock_uow.ranking_snapshots.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_vacancy_ranking_uses_cached_snapshot(mock_uow) -> None:
    vacancy_id = uuid4()
    vacancy = Vacancy(
        id=vacancy_id,
        name="Backend Engineer",
        description="Build backend services.",
        status=VacancyStatus.READY,
        competencies=[],
    )
    cached = VacancyRankingDTO(
        vacancy_id=vacancy_id,
        rankings=[
            RankingItemDTO(
                candidate_id=uuid4(),
                candidate_external_id="candidate-1",
                total_score=79.0,
                required_match=0.7,
                desired_match=1.0,
                required_score=49.0,
                desired_score=30.0,
                breakdown=[
                    RankingBreakdownItemDTO(
                        competency_id=uuid4(),
                        competency_name="Backend",
                        required=True,
                        matched_weight=0.7,
                        total_weight=1.0,
                        coverage=0.7,
                        score_contribution=49.0,
                        matched_subcompetency_ids=[uuid4()],
                        total_subcompetency_ids=[uuid4()],
                    )
                ],
            )
        ],
    )
    snapshot = RankingSnapshot(
        id=uuid4(),
        vacancy_id=vacancy_id,
        payload=RankingSnapshotPayload(data=cached.model_dump(mode="json")),
        calculated_at=datetime.now(UTC),
    )
    mock_uow.vacancies.get.return_value = vacancy
    mock_uow.ranking_snapshots.get_by_vacancy.return_value = snapshot

    result = await GetVacancyRankingUseCase(mock_uow).execute(vacancy_id)

    assert result.vacancy_id == vacancy_id
    assert result.rankings[0].candidate_external_id == "candidate-1"
    mock_uow.candidates.list_by_vacancy.assert_not_awaited()
