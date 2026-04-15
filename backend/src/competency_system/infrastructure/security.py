from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from competency_system.application.dtos.auth import (
    AccessTokenDataDTO,
    GeneratedTokenDTO,
    RefreshTokenDataDTO,
)
from competency_system.infrastructure.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().public_api_prefix}/auth/login"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def hash_value(value: str) -> str:
    return cast(str, pwd_context.hash(value))


def _generate_token(
    data: dict[str, Any],
    *,
    expires_delta: timedelta,
    secret_key: str,
    algorithm: str,
) -> GeneratedTokenDTO:
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return GeneratedTokenDTO(token=encoded_jwt, expiration_time=expire)


def create_access_token(data: AccessTokenDataDTO) -> GeneratedTokenDTO:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _generate_token(
        {
            "sub": str(data.user_id),
            "role": data.role,
        },
        expires_delta=expires_delta,
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(data: RefreshTokenDataDTO) -> GeneratedTokenDTO:
    settings = get_settings()
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    return _generate_token(
        {
            "sub": str(data.user_id),
            "jti": str(data.jti),
        },
        expires_delta=expires_delta,
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
