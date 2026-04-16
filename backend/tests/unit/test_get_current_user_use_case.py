from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import CurrentUserDTO
from competency_system.application.errors import NotFoundError
from competency_system.application.use_cases.auth import GetCurrentUserUseCase
from competency_system.domain.value_objects.enums import UserRole
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return GetCurrentUserUseCase(uow=mock_uow)


async def test_get_current_user_use_case_returns_user_details(
    use_case: GetCurrentUserUseCase, mock_uow
) -> None:
    user = UserFactory().make({"role": UserRole.EXPERT, "is_active": True})
    mock_uow.users.get.return_value = user

    result = await use_case.execute(CurrentUserDTO(user_id=user.id, role=user.role))

    assert result.id == user.id
    assert result.email == user.email
    assert result.role == user.role
    assert result.is_active is True
    mock_uow.users.get.assert_awaited_once_with(user.id)


async def test_get_current_user_use_case_raises_when_user_not_found(
    use_case: GetCurrentUserUseCase, mock_uow
) -> None:
    missing_id = uuid4()
    mock_uow.users.get.return_value = None

    with pytest.raises(NotFoundError, match="not found"):
        await use_case.execute(CurrentUserDTO(user_id=missing_id, role=UserRole.HR))
