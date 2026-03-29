from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from competency_system.domain.value_objects.enums import UserRole


class LoginDTO(BaseModel):
    email: str
    password: str


class TokenResponseDTO(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str


class AccessTokenDataDTO(BaseModel):
    user_id: UUID
    role: UserRole


class RefreshTokenDataDTO(BaseModel):
    user_id: UUID
    jti: UUID


class GeneratedTokenDTO(BaseModel):
    token: str
    expiration_time: datetime


class CurrentUserDTO(BaseModel):
    user_id: UUID
    role: UserRole
