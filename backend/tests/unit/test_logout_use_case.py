from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import RefreshTokenDataDTO
from competency_system.application.use_cases.auth import LogoutUseCase

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return LogoutUseCase(uow=mock_uow)


@pytest.fixture
def token_data() -> RefreshTokenDataDTO:
    return RefreshTokenDataDTO(user_id=uuid4(), jti=uuid4())


async def test_logout_use_case_revokes_refresh_token(
    use_case: LogoutUseCase, mock_uow, token_data: RefreshTokenDataDTO
) -> None:
    await use_case.execute(token_data)

    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(token_data.jti)


async def test_logout_use_case_calls_revoke_even_when_token_absent(
    use_case: LogoutUseCase, mock_uow, token_data: RefreshTokenDataDTO
) -> None:
    mock_uow.refresh_tokens.revoke.return_value = None

    await use_case.execute(token_data)

    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(token_data.jti)
