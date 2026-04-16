from __future__ import annotations

import pytest

from competency_system.application.use_cases.auth import ListUsersUseCase
from competency_system.domain.value_objects.enums import UserRole
from tests.factories import UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return ListUsersUseCase(uow=mock_uow)


async def test_list_users_use_case_returns_mapped_users(
    use_case: ListUsersUseCase, mock_uow
) -> None:
    users = [
        UserFactory().make({"email": "hr@example.com", "role": UserRole.HR}),
        UserFactory().make({"email": "admin@example.com", "role": UserRole.ADMIN}),
    ]
    mock_uow.users.get_list.return_value = users
    mock_uow.users.count.return_value = 2

    result = await use_case.execute(limit=20, offset=0)

    assert [item.email for item in result.items] == [
        "hr@example.com",
        "admin@example.com",
    ]
    assert result.total == 2
    mock_uow.users.get_list.assert_awaited_once_with(limit=20, offset=0)
    mock_uow.users.count.assert_awaited_once()


async def test_list_users_use_case_returns_empty_list_when_no_users(
    use_case: ListUsersUseCase, mock_uow
) -> None:
    mock_uow.users.get_list.return_value = []
    mock_uow.users.count.return_value = 0

    result = await use_case.execute(limit=20, offset=0)

    assert result.items == []
    assert result.total == 0
