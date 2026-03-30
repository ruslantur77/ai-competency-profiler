from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from competency_system.application.dtos.auth import CurrentUserDTO
from competency_system.application.use_cases.ranking import RecalculateRankingUseCase
from competency_system.domain.entities import (
    Candidate,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.services.ranking_engine import RankingEngine
from competency_system.domain.value_objects.enums import UserRole, VacancyStatus
from competency_system.infrastructure.persistence.models import Base
from competency_system.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from competency_system.presentation.api.dependencies import get_current_user, get_uow
from competency_system.presentation.api.main import app


async def _make_session_factory(
    database_path: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


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
    assert top.required_match == pytest.approx(0.9191450300180579)
    assert top.desired_match == pytest.approx(1.0)
    assert top.required_score == pytest.approx(64.34015210126405)
    assert top.desired_score == pytest.approx(30.0)
    assert top.total_score == pytest.approx(94.34015210126405)
    assert len(top.breakdown) == 2
    assert {item.required for item in top.breakdown} == {True, False}
    assert next(
        item.score_contribution for item in top.breakdown if item.required
    ) == pytest.approx(64.34015210126405)
    assert next(
        item.score_contribution for item in top.breakdown if not item.required
    ) == pytest.approx(30.0)


def test_ranking_engine_handles_missing_required_group() -> None:
    desired_skill = SubCompetency(name="Observability", weight=1.0)
    vacancy = Vacancy(
        name="Backend Engineer",
        description="Build backend services.",
        status=VacancyStatus.READY,
        competencies=[
            Competency(
                category_id=UUID(int=1),
                name="Platform",
                sub_competencies=[desired_skill],
                is_required=False,
            )
        ],
    )
    candidate = Candidate(
        external_id="candidate-1",
        vacancy_id=uuid4(),
        achieved_subcompetency_ids={desired_skill.id},
    )

    score = RankingEngine().rank_candidates(vacancy, [candidate])[0]

    assert score.required_match == pytest.approx(1.0)
    assert score.required_score == pytest.approx(0.0)
    assert score.desired_match == pytest.approx(1.0)
    assert score.desired_score == pytest.approx(100.0)
    assert score.total_score == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_recalculate_ranking_use_case_returns_breakdown(tmp_path: Path) -> None:
    engine, session_factory = await _make_session_factory(
        str(tmp_path / "ranking_use_case.db")
    )
    vacancy, candidates = _build_ranking_fixture()

    async with SQLAlchemyUnitOfWork(session_factory) as uow:
        await uow.vacancies.add(vacancy)
        for candidate in candidates:
            candidate.vacancy_id = vacancy.id
            await uow.candidates.add(candidate)
        await uow.commit()

    try:
        dto = await RecalculateRankingUseCase(
            SQLAlchemyUnitOfWork(session_factory)
        ).execute(vacancy.id)
    finally:
        await engine.dispose()

    assert dto.vacancy_id == vacancy.id
    assert [item.candidate_external_id for item in dto.rankings] == [
        "candidate-full",
        "candidate-required-only",
        "candidate-desired-only",
    ]
    assert dto.rankings[0].required_score == pytest.approx(64.34015210126405)
    assert dto.rankings[0].desired_score == pytest.approx(30.0)
    assert len(dto.rankings[0].breakdown) == 2


def test_ranking_api_exposes_canonical_and_legacy_paths(tmp_path: Path) -> None:
    vacancy, candidates = _build_ranking_fixture()
    engine, session_factory = asyncio.run(
        _make_session_factory(str(tmp_path / "ranking_api.db"))
    )

    async def _seed() -> None:
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.vacancies.add(vacancy)
            for candidate in candidates:
                candidate.vacancy_id = vacancy.id
                await uow.candidates.add(candidate)
            await uow.commit()

    asyncio.run(_seed())

    def override_uow() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(session_factory)

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = lambda: CurrentUserDTO(
        user_id=UUID(int=1),
        role=UserRole.ADMIN,
    )

    try:
        with TestClient(app) as client:
            canonical_response = client.get(f"/api/v1/vacancies/{vacancy.id}/rankings")
            legacy_response = client.get(f"/api/v1/vacancies/{vacancy.id}/ranking")

        assert canonical_response.status_code == 200
        assert legacy_response.status_code == 200
        canonical_payload = canonical_response.json()
        legacy_payload = legacy_response.json()
        assert canonical_payload == legacy_payload
        assert (
            canonical_payload["rankings"][0]["candidate_external_id"]
            == "candidate-full"
        )
        assert canonical_payload["rankings"][0]["breakdown"][0][
            "score_contribution"
        ] == pytest.approx(64.34015210126405)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
