from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import CandidateInclude
from competency_system.domain.entities import Candidate, Vacancy
from competency_system.domain.value_objects.enums import VacancyStatus
from competency_system.infrastructure.persistence.repositories import (
    CandidateRepository,
    CategoryRepository,
    VacancyRepository,
)
from tests.fixtures.domain_graph import build_taxonomy, build_vacancy_with_graph

pytestmark = pytest.mark.integration_repo


async def test_candidate_repository_special_methods_and_replace_achievements(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    vacancy_repo = VacancyRepository(pg_session)
    repo = CandidateRepository(pg_session)

    category, _, sub1, sub2 = build_taxonomy()
    vacancy = Vacancy(
        name="Python", description="Python role", status=VacancyStatus.READY
    )

    await category_repo.add(category)
    await vacancy_repo.add(vacancy)

    candidate = Candidate(
        external_id="cand-1",
        vacancy_id=vacancy.id,
    )
    candidate.achieved_subcompetency_ids = {sub1.id}
    await repo.add(candidate)
    await pg_session.commit()

    loaded = await repo.get(candidate.id, include={CandidateInclude.ACHIEVEMENTS})
    assert loaded is not None
    assert loaded.achieved_subcompetency_ids == {sub1.id}

    by_external = await repo.get_by_external_id(
        "cand-1",
        include={CandidateInclude.ACHIEVEMENTS, CandidateInclude.TEST_RESULTS},
    )
    assert by_external is not None
    assert by_external.id == candidate.id

    listed = await repo.list_by_vacancy(
        vacancy.id,
        include={CandidateInclude.ACHIEVEMENTS},
    )
    assert len(listed) == 1

    candidate.achieved_subcompetency_ids = {sub2.id}
    await repo.add(candidate)
    await pg_session.commit()

    updated = await repo.get(candidate.id, include={CandidateInclude.ACHIEVEMENTS})
    assert updated is not None
    assert updated.achieved_subcompetency_ids == {sub2.id}


async def test_candidate_repository_constraints(pg_session: AsyncSession) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = CandidateRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    await repo.add(Candidate(external_id="dup", vacancy_id=vacancy.id))
    await pg_session.commit()

    with pytest.raises(IntegrityError):
        await repo.add(Candidate(external_id="dup", vacancy_id=vacancy.id))

    await pg_session.rollback()

    with pytest.raises(IntegrityError):
        await repo.add(Candidate(external_id="new", vacancy_id=uuid4()))


async def test_candidate_repository_soft_delete_hides_default(
    pg_session: AsyncSession,
) -> None:
    vacancy_repo = VacancyRepository(pg_session)
    repo = CandidateRepository(pg_session)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    candidate = Candidate(external_id="to-delete", vacancy_id=vacancy.id)
    await repo.add(candidate)
    await pg_session.commit()

    deleted = await repo.soft_delete(candidate.id)
    await pg_session.commit()
    assert deleted is not None
    assert deleted.deleted_at is not None

    assert await repo.get(candidate.id) is None
    assert await repo.get_by_external_id("to-delete") is None
    assert await repo.list_by_vacancy(vacancy.id) == []

    visible = await repo.get(candidate.id, include_deleted=True)
    assert visible is not None
    assert visible.deleted_at is not None


async def test_candidate_repository_loads_vacancy_subcompetencies(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    vacancy_repo = VacancyRepository(pg_session)
    repo = CandidateRepository(pg_session)

    vacancy, category, _, _, _ = build_vacancy_with_graph()
    await category_repo.add(category)
    await vacancy_repo.add(vacancy)

    candidate = Candidate(external_id="cand-with-graph", vacancy_id=vacancy.id)
    await repo.add(candidate)
    await pg_session.commit()

    loaded = await repo.get(
        candidate.id,
        include={CandidateInclude.VACANCY_SUBCOMPETENCIES},
    )

    assert loaded is not None
    assert loaded.vacancy is not None
    assert len(loaded.vacancy.competency_nodes) > 0
    assert len(loaded.vacancy.sub_competency_nodes) > 0
