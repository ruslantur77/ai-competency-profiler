from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevels(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "competency-system"
    debug: bool = False
    environment: str = "local"
    log_level: LogLevels = LogLevels.INFO
    allowed_origins_raw: str = Field(default="", alias="ALLOWED_ORIGINS")

    llm_api_key: str = Field(default="", alias="API_KEY")
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="BASE_URL",
    )
    llm_model: str = Field(default="openai/gpt-oss-20b", alias="MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    llm_retry_attempts: int = Field(default=3, alias="LLM_RETRY_ATTEMPTS")
    llm_max_parallel_requests: int = Field(default=4, alias="LLM_MAX_PARALLEL_REQUESTS")
    llm_stage_timeout_seconds: float = Field(
        default=45.0, alias="LLM_STAGE_TIMEOUT_SECONDS"
    )
    llm_reasoning_max_tokens: int = Field(default=0, alias="LLM_REASONING_MAX_TOKENS")
    testing_system_base_url: str = Field(
        default="http://localhost:9000",
        alias="TESTING_SYSTEM_BASE_URL",
    )
    testing_system_api_token: str = Field(
        default="",
        alias="TESTING_SYSTEM_API_TOKEN",
    )
    testing_system_webhook_secret: str = Field(
        default="",
        alias="TESTING_SYSTEM_WEBHOOK_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    secret_key: str = Field(default="", alias="SECRET_KEY")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        alias="AUTH_COOKIE_SAMESITE",
    )
    bootstrap_admin_email: str = Field(default="", alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="", alias="BOOTSTRAP_ADMIN_PASSWORD")

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "app"
    DB_USER: str = "app"
    DB_PASS: str = "app"  # noqa: S105

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @property
    def DB_URL(self) -> str:  # noqa: N802
        return (
            "postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url(self) -> str:
        return self.DB_URL

    @property
    def resolved_database_url_sync(self) -> str:
        return self.DB_URL.replace("+asyncpg", "+psycopg2")

    @property
    def allowed_origins(self) -> list[str]:
        if not self.allowed_origins_raw.strip():
            return []
        return [
            origin.strip()
            for origin in self.allowed_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
