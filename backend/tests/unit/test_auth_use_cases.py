from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from competency_system.application.dtos.auth import (
    LoginDTO,
    RefreshTokenDataDTO,
    UserCreateDTO,
)
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


@pytest.fixture
def inactive_user() -> User:
    return User(
        email="inactive@example.com",
        hashed_password=hash_value("secret"),
        is_active=False,
    )


@pytest.fixture
def active_admin_user() -> User:
    return User(
        email="admin@example.com",
        hashed_password=hash_value("secret"),
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def active_user() -> User:
    return User(email="user@example.com", hashed_password=hash_value("secret"))


@pytest.fixture
def old_refresh_token_data(active_user: User) -> tuple[UUID, str]:
    old_jti = uuid4()
    raw_token = create_refresh_token(
        RefreshTokenDataDTO(user_id=active_user.id, jti=old_jti)
    ).token
    return old_jti, raw_token


async def test_authenticate_user_returns_none_for_inactive_user(
    mock_uow, inactive_user: User
) -> None:
    mock_uow.users.get_by_email.return_value = inactive_user

    result = await AuthenticateUserUseCase(uow=mock_uow).execute(
        LoginDTO(email="inactive@example.com", password="secret")
    )

    assert result is None


async def test_authenticate_user_returns_user_for_valid_credentials(
    mock_uow, active_admin_user: User
) -> None:
    mock_uow.users.get_by_email.return_value = active_admin_user

    result = await AuthenticateUserUseCase(uow=mock_uow).execute(
        LoginDTO(email="admin@example.com", password="secret")
    )

    assert result is not None
    assert result.id == active_admin_user.id
    assert result.role == UserRole.ADMIN


async def test_issue_token_pair_persists_refresh_token(
    mock_uow, active_user: User
) -> None:
    mock_uow.users.get.return_value = active_user

    token_pair = await IssueTokenPairUseCase(uow=mock_uow).execute(
        user_id=active_user.id
    )

    assert token_pair is not None
    assert token_pair.access_token
    assert token_pair.refresh_token
    mock_uow.refresh_tokens.add_token.assert_awaited_once()


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

    result = await RefreshTokenPairUseCase(uow=mock_uow).execute(
        refresh_token_raw=raw_token,
        token_data=RefreshTokenDataDTO(user_id=user_id, jti=jti),
    )

    assert result is None
    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(jti)


async def test_refresh_token_pair_rotates_tokens_for_valid_token(
    mock_uow,
    active_user: User,
    old_refresh_token_data: tuple[UUID, str],
) -> None:
    old_jti, raw_token = old_refresh_token_data
    stored = RefreshToken(
        jti=old_jti,
        user_id=active_user.id,
        token_hash=hash_value(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    mock_uow.refresh_tokens.get_by_jti.return_value = stored
    mock_uow.users.get.return_value = active_user

    result = await RefreshTokenPairUseCase(uow=mock_uow).execute(
        refresh_token_raw=raw_token,
        token_data=RefreshTokenDataDTO(user_id=active_user.id, jti=old_jti),
    )

    assert result is not None
    assert result.access_token
    assert result.refresh_token
    assert mock_uow.refresh_tokens.revoke.await_count == 1
    assert mock_uow.refresh_tokens.add_token.await_count == 1


async def test_create_user_rejects_duplicate_email(mock_uow) -> None:
    mock_uow.users.get_by_email.return_value = User(
        email="duplicate@example.com",
        hashed_password=hash_value("secret"),
    )

    with pytest.raises(ValueError, match="already exists"):
        await CreateUserUseCase(uow=mock_uow).execute(
            UserCreateDTO(
                email="duplicate@example.com",
                password="secret",
                role=UserRole.HR,
            )
        )


async def test_logout_revokes_refresh_token(mock_uow) -> None:
    token_data = RefreshTokenDataDTO(user_id=uuid4(), jti=uuid4())

    await LogoutUseCase(uow=mock_uow).execute(token_data)

    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(token_data.jti)
