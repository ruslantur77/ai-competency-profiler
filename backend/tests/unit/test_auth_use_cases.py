from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from competency_system.application.dtos.auth import LoginDTO, RefreshTokenDataDTO, UserCreateDTO
from competency_system.application.use_cases.auth import (
    AuthenticateUserUseCase,
    CreateUserUseCase,
    IssueTokenPairUseCase,
    LogoutUseCase,
    RefreshTokenPairUseCase,
)
from competency_system.domain.entities import RefreshToken, User
from competency_system.domain.value_objects.enums import UserRole
from competency_system.infrastructure.security import create_refresh_token, hash_value

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_for_inactive_user(mock_uow) -> None:
    user = User(
        email="inactive@example.com",
        hashed_password=hash_value("secret"),
        is_active=False,
    )
    mock_uow.users.get_by_email.return_value = user

    result = await AuthenticateUserUseCase(mock_uow.users).execute(
        LoginDTO(email="inactive@example.com", password="secret")
    )

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_returns_user_for_valid_credentials(mock_uow) -> None:
    user = User(
        email="admin@example.com",
        hashed_password=hash_value("secret"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    mock_uow.users.get_by_email.return_value = user

    result = await AuthenticateUserUseCase(mock_uow.users).execute(
        LoginDTO(email="admin@example.com", password="secret")
    )

    assert result is not None
    assert result.id == user.id
    assert result.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_issue_token_pair_persists_refresh_token(mock_uow) -> None:
    user = User(email="user@example.com", hashed_password=hash_value("secret"))
    mock_uow.users.get.return_value = user
    use_case = IssueTokenPairUseCase(
        user_repo=mock_uow.users,
        refresh_token_repo=mock_uow.refresh_tokens,
    )

    token_pair = await use_case.execute(user_id=user.id)

    assert token_pair is not None
    assert token_pair.access_token
    assert token_pair.refresh_token
    mock_uow.refresh_tokens.add_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_token_pair_revokes_expired_token(mock_uow) -> None:
    user_id = uuid4()
    jti = uuid4()
    raw_token = "irrelevant"
    stored = RefreshToken(
        jti=jti,
        user_id=user_id,
        token_hash=hash_value("token"),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    mock_uow.refresh_tokens.get_by_jti.return_value = stored
    use_case = RefreshTokenPairUseCase(
        user_repo=mock_uow.users,
        refresh_token_repo=mock_uow.refresh_tokens,
    )

    result = await use_case.execute(
        refresh_token_raw=raw_token,
        token_data=RefreshTokenDataDTO(user_id=user_id, jti=jti),
    )

    assert result is None
    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(jti)


@pytest.mark.asyncio
async def test_refresh_token_pair_rotates_tokens_for_valid_token(mock_uow) -> None:
    user = User(email="user@example.com", hashed_password=hash_value("secret"))
    old_jti = uuid4()
    raw_token = create_refresh_token(RefreshTokenDataDTO(user_id=user.id, jti=old_jti)).token
    stored = RefreshToken(
        jti=old_jti,
        user_id=user.id,
        token_hash=hash_value(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    mock_uow.refresh_tokens.get_by_jti.return_value = stored
    mock_uow.users.get.return_value = user
    use_case = RefreshTokenPairUseCase(
        user_repo=mock_uow.users,
        refresh_token_repo=mock_uow.refresh_tokens,
    )

    result = await use_case.execute(
        refresh_token_raw=raw_token,
        token_data=RefreshTokenDataDTO(user_id=user.id, jti=old_jti),
    )

    assert result is not None
    assert result.access_token
    assert result.refresh_token
    assert mock_uow.refresh_tokens.revoke.await_count == 1
    assert mock_uow.refresh_tokens.add_token.await_count == 1


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(mock_uow) -> None:
    mock_uow.users.get_by_email.return_value = User(
        email="duplicate@example.com",
        hashed_password=hash_value("secret"),
    )
    use_case = CreateUserUseCase(mock_uow.users)

    with pytest.raises(ValueError, match="already exists"):
        await use_case.execute(
            UserCreateDTO(
                email="duplicate@example.com",
                password="secret",
                role=UserRole.HR,
            )
        )


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(mock_uow) -> None:
    token_data = RefreshTokenDataDTO(user_id=uuid4(), jti=uuid4())
    use_case = LogoutUseCase(mock_uow.refresh_tokens)

    await use_case.execute(token_data)

    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(token_data.jti)
