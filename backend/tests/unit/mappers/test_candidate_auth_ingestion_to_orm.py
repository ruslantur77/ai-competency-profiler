from __future__ import annotations

import pytest

from competency_system.application.dtos.webhooks import (
    RankingSnapshotPayload,
    WebhookEventPayload,
)
from competency_system.infrastructure.persistence.mappers import (
    candidate_to_orm,
    ranking_snapshot_to_orm,
    refresh_token_to_orm,
    user_to_orm,
    webhook_event_to_orm,
)
from competency_system.infrastructure.persistence.models import UNSET
from tests.factories import (
    CandidateFactory,
    RankingSnapshotFactory,
    RefreshTokenFactory,
    UserFactory,
    VacancyFactory,
    WebhookEventFactory,
)

from .conftest import PolicyCase, assert_field_omitted, assert_field_set


def test_candidate_to_orm_default_scalar_only(policy_case: PolicyCase) -> None:
    vacancy = VacancyFactory().make()
    candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
    candidate.vacancy = vacancy

    orm = candidate_to_orm(candidate, policy=policy_case.policy)

    assert orm.vacancy_id == vacancy.id
    assert_field_omitted(orm, "vacancy")


def test_candidate_last_assessment_none_by_policy(policy_case: PolicyCase) -> None:
    candidate = CandidateFactory().make({"last_assessment_at": None})

    orm = candidate_to_orm(candidate, policy=policy_case.policy)
    if policy_case.applies_scalar_none:
        assert_field_set(orm, "last_assessment_at")
        assert orm.last_assessment_at is None
    else:
        assert_field_omitted(orm, "last_assessment_at")


def test_candidate_unset_ignored_even_if_present(policy_case: PolicyCase) -> None:
    candidate = CandidateFactory().make({"last_assessment_at": None})
    candidate.last_assessment_at = UNSET  # type: ignore[assignment]
    orm = candidate_to_orm(
        candidate,
        present_fields={"last_assessment_at"},
        policy=policy_case.policy,
    )
    assert_field_omitted(orm, "last_assessment_at")


def test_user_relationship_none_policy(policy_case: PolicyCase) -> None:
    user = UserFactory().make()
    user.refresh_tokens = None  # type: ignore[assignment]
    if policy_case.applies_relationship_none:
        with pytest.raises(TypeError):
            user_to_orm(
                user,
                present_fields={"refresh_tokens"},
                policy=policy_case.policy,
            )
        return

    orm = user_to_orm(
        user,
        present_fields={"refresh_tokens"},
        policy=policy_case.policy,
    )
    assert_field_omitted(orm, "refresh_tokens")


def test_refresh_token_scalar_none_by_policy(policy_case: PolicyCase) -> None:
    token = RefreshTokenFactory().make({"revoked_at": None})
    orm = refresh_token_to_orm(token, policy=policy_case.policy)
    if policy_case.applies_scalar_none:
        assert_field_set(orm, "revoked_at")
        assert orm.revoked_at is None
    else:
        assert_field_omitted(orm, "revoked_at")


def test_webhook_event_payload_serialized_to_dict(policy_case: PolicyCase) -> None:
    event = WebhookEventFactory().make({"payload": WebhookEventPayload(data={"a": 1})})
    orm = webhook_event_to_orm(event, policy=policy_case.policy)
    assert orm.payload == {"a": 1}


def test_ranking_snapshot_payload_serialized_to_dict(policy_case: PolicyCase) -> None:
    snapshot = RankingSnapshotFactory().make(
        {"payload": RankingSnapshotPayload(data={"items": [1]})}
    )
    orm = ranking_snapshot_to_orm(snapshot, policy=policy_case.policy)
    assert orm.payload == {"items": [1]}
