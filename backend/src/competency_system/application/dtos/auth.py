from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr

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


class CurrentUserDetailsDTO(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool


class UserAdminDTO(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.HR


class UserRoleUpdateDTO(BaseModel):
    role: UserRole


class UserStatusUpdateDTO(BaseModel):
    is_active: bool
