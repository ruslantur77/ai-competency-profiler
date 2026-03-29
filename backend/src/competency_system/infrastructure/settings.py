from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "competency-system"
    debug: bool = False
    environment: str = "local"
    log_level: str = "info"
    allowed_origins_raw: str = Field(default="", alias="ALLOWED_ORIGINS")

    llm_api_key: str = Field(default="", alias="API_KEY")
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="BASE_URL",
    )
    llm_model: str = Field(default="openai/gpt-oss-20b:free", alias="MODEL")
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

    database_url: str = Field(
        default="postgresql+asyncpg://app:app@localhost/app",
        alias="DATABASE_URL",
    )
    database_url_sync: str | None = Field(
        default=None,
        alias="DATABASE_URL_SYNC",
    )

    @property
    def resolved_database_url_sync(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        if "+asyncpg" in self.database_url:
            return self.database_url.replace("+asyncpg", "+psycopg2")
        return self.database_url

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
