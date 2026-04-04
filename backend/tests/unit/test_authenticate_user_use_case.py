from __future__ import annotations

import pytest

from competency_system.application.dtos.auth import LoginDTO
from competency_system.application.use_cases.auth import AuthenticateUserUseCase
from competency_system.infrastructure.security import hash_value
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return AuthenticateUserUseCase(uow=mock_uow)


@pytest.fixture
def credentials() -> LoginDTO:
    return LoginDTO(email="admin@example.com", password="secret")


async def test_authenticate_user_use_case_returns_user_for_valid_credentials(
    use_case: AuthenticateUserUseCase, mock_uow, credentials: LoginDTO
) -> None:
    user = UserFactory().make(
        {
            "email": credentials.email,
            "hashed_password": hash_value(credentials.password),
            "is_active": True,
        }
    )
    mock_uow.users.get_by_email.return_value = user

    result = await use_case.execute(credentials)

    assert result is not None
    assert result.id == user.id
    mock_uow.users.get_by_email.assert_awaited_once_with(credentials.email)


async def test_authenticate_user_use_case_returns_none_for_inactive_user(
    use_case: AuthenticateUserUseCase, mock_uow, credentials: LoginDTO
) -> None:
    user = UserFactory().make(
        {
            "email": credentials.email,
            "hashed_password": hash_value(credentials.password),
            "is_active": False,
        }
    )
    mock_uow.users.get_by_email.return_value = user

    result = await use_case.execute(credentials)

    assert result is None
