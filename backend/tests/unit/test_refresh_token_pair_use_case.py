from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import RefreshTokenDataDTO
from competency_system.application.use_cases.auth import RefreshTokenPairUseCase
from competency_system.infrastructure.security import create_refresh_token, hash_value
from tests.factories import RefreshTokenFactory, UserFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def use_case(mock_uow):
    return RefreshTokenPairUseCase(uow=mock_uow)


@pytest.fixture
def active_user():
    return UserFactory().make(
        {"email": "user@example.com", "hashed_password": hash_value("secret")}
    )


async def test_refresh_token_pair_use_case_rotates_tokens_for_valid_token(
    use_case: RefreshTokenPairUseCase, mock_uow, active_user
) -> None:
    old_jti = uuid4()
    raw_token = create_refresh_token(
        RefreshTokenDataDTO(user_id=active_user.id, jti=old_jti)
    ).token
    stored = RefreshTokenFactory().make(
        {
            "jti": old_jti,
            "user_id": active_user.id,
            "token_hash": hash_value(raw_token),
            "expires_at": datetime.now(UTC) + timedelta(days=1),
        }
    )
    mock_uow.refresh_tokens.get_by_jti.return_value = stored
    mock_uow.users.get.return_value = active_user

    result = await use_case.execute(
        refresh_token_raw=raw_token,
        token_data=RefreshTokenDataDTO(user_id=active_user.id, jti=old_jti),
    )

    assert result is not None
    assert result.access_token
    assert result.refresh_token
    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(old_jti)
    mock_uow.refresh_tokens.add_token.assert_awaited_once()


async def test_refresh_token_pair_use_case_revokes_expired_token(
    use_case: RefreshTokenPairUseCase, mock_uow
) -> None:
    user_id = uuid4()
    jti = uuid4()
    mock_uow.refresh_tokens.get_by_jti.return_value = RefreshTokenFactory().make(
        {
            "jti": jti,
            "user_id": user_id,
            "token_hash": hash_value("token"),
            "expires_at": datetime.now(UTC) - timedelta(minutes=1),
        }
    )

    result = await use_case.execute(
        refresh_token_raw="irrelevant",
        token_data=RefreshTokenDataDTO(user_id=user_id, jti=jti),
    )

    assert result is None
    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(jti)
