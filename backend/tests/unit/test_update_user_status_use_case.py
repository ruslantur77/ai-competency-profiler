from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import UserStatusUpdateDTO
from competency_system.application.use_cases.auth import UpdateUserStatusUseCase
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return UpdateUserStatusUseCase(uow=mock_uow)


@pytest.fixture
def status_update() -> UserStatusUpdateDTO:
    return UserStatusUpdateDTO(is_active=False)


async def test_update_user_status_use_case_updates_status(
    use_case: UpdateUserStatusUseCase, mock_uow, status_update: UserStatusUpdateDTO
) -> None:
    user = UserFactory().make({"is_active": True})
    mock_uow.users.get.return_value = user

    result = await use_case.execute(user.id, status_update)

    assert result.is_active is False
    mock_uow.users.add.assert_awaited_once_with(user)


async def test_update_user_status_use_case_raises_when_user_not_found(
    use_case: UpdateUserStatusUseCase, mock_uow, status_update: UserStatusUpdateDTO
) -> None:
    mock_uow.users.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4(), status_update)
