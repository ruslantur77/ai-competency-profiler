from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.domain.entities import Category, Competency, SubCompetency
from competency_system.infrastructure.persistence.repositories import (
    CategoryRepository,
    CompetencyRepository,
    SubCompetencyRepository,
)

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_subcompetency_repository_crud(pg_session: AsyncSession) -> None:
    category_repo = CategoryRepository(pg_session)
    competency_repo = CompetencyRepository(pg_session)
    repo = SubCompetencyRepository(pg_session)

    category = Category(name="Data")
    await category_repo.add(category)

    sub = SubCompetency(name="Modeling")
    competency = Competency(
        category_id=category.id,
        name="Databases",
        sub_competencies=[sub],
    )
    await competency_repo.add(competency)
    await pg_session.commit()

    loaded = await repo.get(sub.id)
    assert loaded is not None
    assert loaded.name == "Modeling"

    await repo.delete(sub.id)
    await pg_session.commit()

    assert await repo.get(sub.id) is None
