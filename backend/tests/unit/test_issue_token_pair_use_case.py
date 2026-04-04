from __future__ import annotations

import pytest

from competency_system.application.use_cases.auth import IssueTokenPairUseCase
from competency_system.infrastructure.security import hash_value
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return IssueTokenPairUseCase(uow=mock_uow)


@pytest.fixture
def active_user():
    return UserFactory().make(
        {"email": "user@example.com", "hashed_password": hash_value("secret")}
    )


async def test_issue_token_pair_use_case_persists_refresh_token(
    use_case: IssueTokenPairUseCase, mock_uow, active_user
) -> None:
    mock_uow.users.get.return_value = active_user

    result = await use_case.execute(user_id=active_user.id)

    assert result is not None
    assert result.access_token
    assert result.refresh_token
    mock_uow.refresh_tokens.add_token.assert_awaited_once()


async def test_issue_token_pair_use_case_returns_none_for_inactive_user(
    use_case: IssueTokenPairUseCase, mock_uow
) -> None:
    inactive_user = UserFactory().make(
        {
            "email": "inactive@example.com",
            "hashed_password": hash_value("secret"),
            "is_active": False,
        }
    )
    mock_uow.users.get.return_value = inactive_user

    result = await use_case.execute(user_id=inactive_user.id)

    assert result is None
    mock_uow.refresh_tokens.add_token.assert_not_awaited()
