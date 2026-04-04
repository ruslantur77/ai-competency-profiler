from __future__ import annotations

from dataclasses import dataclass

import pytest

from competency_system.infrastructure.persistence.models import (
    POLICY_DEFAULT_LIGHT,
    POLICY_IGNORE_NONE,
    POLICY_STRICT,
    DumpPolicy,
    RelationshipEmptyCollectionPolicy,
    RelationshipNonePolicy,
    ScalarNonePolicy,
)


@dataclass(frozen=True, slots=True)
class PolicyCase:
    name: str
    policy: DumpPolicy

    @property
    def applies_scalar_none(self) -> bool:
        return self.policy.scalar_none is ScalarNonePolicy.APPLY

    @property
    def applies_relationship_none(self) -> bool:
        return self.policy.relationship_none is RelationshipNonePolicy.APPLY

    @property
    def applies_empty_relationship(self) -> bool:
        return (
            self.policy.relationship_empty_collection
            is RelationshipEmptyCollectionPolicy.APPLY
        )


ALL_POLICY_CASES = (
    PolicyCase(name="default_light", policy=POLICY_DEFAULT_LIGHT),
    PolicyCase(name="strict", policy=POLICY_STRICT),
    PolicyCase(name="ignore_none", policy=POLICY_IGNORE_NONE),
)


@pytest.fixture(params=ALL_POLICY_CASES, ids=lambda c: c.name)
def policy_case(request: pytest.FixtureRequest) -> PolicyCase:
    case = request.param
    assert isinstance(case, PolicyCase)
    return case


def assert_field_set(orm: object, field_name: str) -> None:
    assert field_name in orm.__dict__


def assert_field_omitted(orm: object, field_name: str) -> None:
    assert field_name not in orm.__dict__
