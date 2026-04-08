from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import UserRoleUpdateDTO
from competency_system.application.use_cases.auth import UpdateUserRoleUseCase
from competency_system.domain.value_objects.enums import UserRole
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return UpdateUserRoleUseCase(uow=mock_uow)


@pytest.fixture
def role_update() -> UserRoleUpdateDTO:
    return UserRoleUpdateDTO(role=UserRole.ADMIN)


async def test_update_user_role_use_case_updates_role(
    use_case: UpdateUserRoleUseCase, mock_uow, role_update: UserRoleUpdateDTO
) -> None:
    user = UserFactory().make({"role": UserRole.HR})
    mock_uow.users.get.return_value = user

    result = await use_case.execute(user.id, role_update)

    assert result.role == UserRole.ADMIN
    mock_uow.users.add.assert_awaited_once_with(user)
    mock_uow.commit.assert_awaited_once()


async def test_update_user_role_use_case_raises_when_user_not_found(
    use_case: UpdateUserRoleUseCase, mock_uow, role_update: UserRoleUpdateDTO
) -> None:
    mock_uow.users.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4(), role_update)
    mock_uow.commit.assert_not_awaited()
