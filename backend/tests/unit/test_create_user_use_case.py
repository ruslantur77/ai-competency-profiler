from __future__ import annotations

import pytest

from competency_system.application.dtos.auth import UserCreateDTO
from competency_system.application.use_cases.auth import CreateUserUseCase
from competency_system.domain.value_objects.enums import UserRole
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return CreateUserUseCase(uow=mock_uow)


@pytest.fixture
def command() -> UserCreateDTO:
    return UserCreateDTO(email="new@example.com", password="secret", role=UserRole.HR)


async def test_create_user_use_case_creates_user(
    use_case: CreateUserUseCase, mock_uow, command: UserCreateDTO
) -> None:
    mock_uow.users.get_by_email.return_value = None

    result = await use_case.execute(command)

    assert result.email == command.email
    assert result.role == command.role
    mock_uow.users.add.assert_awaited_once()


async def test_create_user_use_case_rejects_duplicate_email(
    use_case: CreateUserUseCase, mock_uow, command: UserCreateDTO
) -> None:
    mock_uow.users.get_by_email.return_value = UserFactory().make(
        {"email": command.email}
    )

    with pytest.raises(ValueError, match="already exists"):
        await use_case.execute(command)
