from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.infrastructure.persistence.mappers import (
    category_to_orm,
    competency_to_orm,
    subcompetency_to_orm,
)
from tests.factories import CategoryFactory, CompetencyFactory, SubCompetencyFactory

from .conftest import PolicyCase, assert_field_omitted, assert_field_set


@pytest.mark.parametrize("with_items", [False, True], ids=["empty", "non_empty"])
def test_category_to_orm_relationship_collection_policy(
    policy_case: PolicyCase,
    with_items: bool,
) -> None:
    category_factory = CategoryFactory()
    competency_factory = CompetencyFactory()
    sub_factory = SubCompetencyFactory()

    competencies = []
    if with_items:
        sub = sub_factory.make()
        competency = competency_factory.make({"sub_competencies": [sub]})
        sub.competency_id = competency.id
        competencies = [competency]
    category = category_factory.make({"competencies": competencies})

    orm = category_to_orm(
        category,
        present_fields={"competencies", "competencies.sub_competencies"},
        policy=policy_case.policy,
    )

    if with_items:
        assert_field_set(orm, "competencies")
        assert len(orm.competencies) == 1
        assert orm.competencies[0].name == category.competencies[0].name
        assert len(orm.competencies[0].sub_competencies) == 1
    elif policy_case.applies_empty_relationship:
        assert_field_set(orm, "competencies")
        assert orm.competencies == []
    else:
        assert_field_omitted(orm, "competencies")


def test_category_to_orm_handles_cycle(policy_case: PolicyCase) -> None:
    category_factory = CategoryFactory()
    competency_factory = CompetencyFactory()
    sub_factory = SubCompetencyFactory()

    category = category_factory.make()
    competency = competency_factory.make(
        {"category_id": category.id, "category": category}
    )
    sub = sub_factory.make({"competency_id": competency.id, "competency": competency})
    competency.sub_competencies = [sub]
    category.competencies = [competency]

    orm = category_to_orm(
        category,
        present_fields={
            "competencies",
            "competencies.category",
            "competencies.sub_competencies",
            "competencies.sub_competencies.competency",
        },
        policy=policy_case.policy,
    )

    assert len(orm.competencies) == 1
    if policy_case.applies_relationship_none:
        assert orm.competencies[0].category is orm
        assert orm.competencies[0].sub_competencies[0].competency is orm.competencies[0]


def test_competency_to_orm_relationship_none_policy(policy_case: PolicyCase) -> None:
    competency = CompetencyFactory().make({"category_id": uuid4(), "category": None})

    orm = competency_to_orm(
        competency,
        present_fields={"category"},
        policy=policy_case.policy,
    )

    if policy_case.applies_relationship_none:
        assert_field_set(orm, "category")
        assert orm.category is None
    else:
        assert_field_omitted(orm, "category")


def test_subcompetency_to_orm_relationship_none_policy(policy_case: PolicyCase) -> None:
    sub = SubCompetencyFactory().make({"competency_id": uuid4(), "competency": None})

    orm = subcompetency_to_orm(
        sub,
        present_fields={"competency"},
        policy=policy_case.policy,
    )

    if policy_case.applies_relationship_none:
        assert_field_set(orm, "competency")
        assert orm.competency is None
    else:
        assert_field_omitted(orm, "competency")
