from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import CategoryInclude
from competency_system.infrastructure.persistence.repositories import CategoryRepository

from .helpers import build_taxonomy

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_category_repository_crud_and_includes(pg_session: AsyncSession) -> None:
    repo = CategoryRepository(pg_session)
    category, _, _, _ = build_taxonomy()

    await repo.add(category)
    await pg_session.commit()

    loaded = await repo.get(category.id)
    assert loaded is not None
    assert loaded.name == category.name

    with_competencies = await repo.get(
        category.id,
        include={CategoryInclude.COMPETENCIES},
    )
    assert with_competencies is not None
    assert len(with_competencies.competencies) == 1

    with_subs = await repo.get(
        category.id,
        include={CategoryInclude.SUB_COMPETENCIES},
    )
    assert with_subs is not None
    assert len(with_subs.competencies[0].sub_competencies) == 2

    listed = await repo.list(include={CategoryInclude.SUB_COMPETENCIES})
    assert len(listed) == 1

    await repo.delete(category.id)
    await pg_session.commit()

    assert await repo.get(category.id) is None
