from __future__ import annotations

import pytest

from competency_system.domain.value_objects.enums import SuggestionStatus
from competency_system.infrastructure.persistence.mappers import (
    vacancy_category_node_to_orm,
    vacancy_competency_node_to_orm,
    vacancy_sub_competency_node_to_orm,
    vacancy_suggestion_to_orm,
    vacancy_to_orm,
)
from tests.factories import (
    CategoryFactory,
    CompetencyFactory,
    SubCompetencyFactory,
    VacancyCategoryNodeFactory,
    VacancyCompetencyNodeFactory,
    VacancyFactory,
    VacancyGraphSuggestionFactory,
    VacancySubCompetencyNodeFactory,
)

from .conftest import PolicyCase, assert_field_omitted, assert_field_set


def test_vacancy_to_orm_default_present_fields_are_scalar_only(
    policy_case: PolicyCase,
) -> None:
    category = CategoryFactory().make()
    competency = CompetencyFactory().make({"category_id": category.id})
    sub = SubCompetencyFactory().make({"competency_id": competency.id})
    node = VacancySubCompetencyNodeFactory().make(
        {
            "sub_competency_id": sub.id,
            "competency_id": competency.id,
        }
    )
    vacancy = VacancyFactory().make({"sub_competency_nodes": [node]})

    orm = vacancy_to_orm(vacancy, policy=policy_case.policy)

    assert_field_set(orm, "name")
    assert_field_omitted(orm, "sub_competency_nodes")


@pytest.mark.parametrize("as_empty", [False, True], ids=["none", "empty"])
def test_vacancy_to_orm_collection_relationship_policy(
    policy_case: PolicyCase,
    as_empty: bool,
) -> None:
    vacancy = VacancyFactory().make({"category_nodes": []})
    if not as_empty:
        vacancy.category_nodes = None  # type: ignore[assignment]

    if not as_empty and policy_case.applies_relationship_none:
        with pytest.raises(TypeError):
            vacancy_to_orm(
                vacancy,
                present_fields={"category_nodes"},
                policy=policy_case.policy,
            )
        return

    orm = vacancy_to_orm(
        vacancy,
        present_fields={"category_nodes"},
        policy=policy_case.policy,
    )

    if as_empty:
        if policy_case.applies_empty_relationship:
            assert_field_set(orm, "category_nodes")
            assert orm.category_nodes == []
        else:
            assert_field_omitted(orm, "category_nodes")
    else:
        assert_field_omitted(orm, "category_nodes")


def test_vacancy_category_node_to_orm_relationship_none(
    policy_case: PolicyCase,
) -> None:
    node = VacancyCategoryNodeFactory().make({"vacancy": None, "category": None})
    orm = vacancy_category_node_to_orm(
        node,
        present_fields={"vacancy", "category"},
        policy=policy_case.policy,
    )
    if policy_case.applies_relationship_none:
        assert orm.vacancy is None
        assert orm.category is None
    else:
        assert_field_omitted(orm, "vacancy")
        assert_field_omitted(orm, "category")


def test_vacancy_competency_node_to_orm_relationship_none(
    policy_case: PolicyCase,
) -> None:
    node = VacancyCompetencyNodeFactory().make(
        {"vacancy": None, "category": None, "competency": None}
    )
    orm = vacancy_competency_node_to_orm(
        node,
        present_fields={"vacancy", "category", "competency"},
        policy=policy_case.policy,
    )
    for field in ("vacancy", "category", "competency"):
        if policy_case.applies_relationship_none:
            assert_field_set(orm, field)
        else:
            assert_field_omitted(orm, field)


def test_vacancy_sub_competency_node_to_orm_relationship_none(
    policy_case: PolicyCase,
) -> None:
    node = VacancySubCompetencyNodeFactory().make(
        {"vacancy": None, "sub_competency": None, "competency": None}
    )
    orm = vacancy_sub_competency_node_to_orm(
        node,
        present_fields={"vacancy", "sub_competency", "competency"},
        policy=policy_case.policy,
    )
    for field in ("vacancy", "sub_competency", "competency"):
        if policy_case.applies_relationship_none:
            assert_field_set(orm, field)
        else:
            assert_field_omitted(orm, field)


def test_vacancy_suggestion_scalar_none_by_policy(policy_case: PolicyCase) -> None:
    suggestion = VacancyGraphSuggestionFactory().make(
        {
            "status": SuggestionStatus.APPROVED,
            "parent_category_id": None,
            "parent_competency_id": None,
            "is_required": None,
            "target_level": None,
            "weight": None,
        }
    )
    orm = vacancy_suggestion_to_orm(suggestion, policy=policy_case.policy)

    for field in (
        "parent_category_id",
        "parent_competency_id",
        "is_required",
        "target_level",
        "weight",
    ):
        if policy_case.applies_scalar_none:
            assert_field_set(orm, field)
            assert getattr(orm, field) is None
        else:
            assert_field_omitted(orm, field)


def test_vacancy_suggestion_relationship_none_by_policy(
    policy_case: PolicyCase,
) -> None:
    suggestion = VacancyGraphSuggestionFactory().make()
    suggestion.vacancy = None
    suggestion.parent_category = None
    suggestion.parent_competency = None

    orm = vacancy_suggestion_to_orm(
        suggestion,
        present_fields={"vacancy", "parent_category", "parent_competency"},
        policy=policy_case.policy,
    )
    for field in ("vacancy", "parent_category", "parent_competency"):
        if policy_case.applies_relationship_none:
            assert_field_set(orm, field)
        else:
            assert_field_omitted(orm, field)
