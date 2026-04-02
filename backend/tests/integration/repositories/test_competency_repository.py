from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import CompetencyInclude
from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    CompetencyRepository,
)

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_competency_repository_crud_and_include(pg_session: AsyncSession) -> None:
    category_repo = CategoryRepository(pg_session)
    repo = CompetencyRepository(pg_session)

    category = Category(name="Data")
    await category_repo.add(category)

    sub = SubCompetency(name="Modeling")
    competency = Competency(
        category_id=category.id,
        name="Databases",
        sub_competencies=[sub],
    )
    await repo.add(competency)
    await pg_session.commit()

    loaded = await repo.get(
        competency.id,
        include={CompetencyInclude.CATEGORY, CompetencyInclude.SUB_COMPETENCIES},
    )
    assert loaded is not None
    assert loaded.name == "Databases"
    assert len(loaded.sub_competencies) == 1

    listed = await repo.get_list(include={CompetencyInclude.SUB_COMPETENCIES})
    assert len(listed) == 1

    await repo.delete(competency.id)
    await pg_session.commit()

    assert await repo.get(competency.id) is None
