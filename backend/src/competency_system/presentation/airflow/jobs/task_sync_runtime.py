from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaskSyncRunnerConfig:
    debug: bool
    environment: str
    log_level: str
    database_url: str
    testing_system_base_url: str
    testing_system_api_token: str
    llm_queue_backend: str
    redis_host: str
    redis_port: int
    redis_password: str
    celery_queue_name: str
    celery_result_expires_seconds: int

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/0"


def env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    return int(value)


def normalize_database_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql+psycopg2://"):
        return value.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return value


def build_database_url_from_db_env() -> str:
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASS")
    values: dict[str, str] = {}
    missing: list[str] = []
    for key in required:
        value = os.getenv(key)
        if value is None or value == "":
            missing.append(key)
            continue
        values[key] = value
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            "Database configuration is incomplete. Provide DATABASE_URL "
            f"or all DB_* variables. Missing: {missing_str}"
        )
    return (
        "postgresql+asyncpg://"
        f"{values['DB_USER']}:{values['DB_PASS']}@"
        f"{values['DB_HOST']}:{values['DB_PORT']}/{values['DB_NAME']}"
    )


def load_runner_config() -> TaskSyncRunnerConfig:
    database_url_env = os.getenv("DATABASE_URL")
    database_url = (
        normalize_database_url(database_url_env)
        if database_url_env
        else build_database_url_from_db_env()
    )
    return TaskSyncRunnerConfig(
        debug=env_bool("DEBUG", False),
        environment=os.getenv("ENVIRONMENT", "local"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=database_url,
        testing_system_base_url=os.getenv(
            "TESTING_SYSTEM_BASE_URL",
            "http://localhost:9000",
        ),
        testing_system_api_token=os.getenv("TESTING_SYSTEM_API_TOKEN", ""),
        llm_queue_backend=os.getenv("LLM_QUEUE_BACKEND", "inmemory").lower(),
        redis_host=os.getenv("REDIS_HOST", "127.0.0.1"),
        redis_port=env_int("REDIS_PORT", 6379),
        redis_password=os.getenv("REDIS_PASSWORD", ""),
        celery_queue_name=os.getenv("CELERY_QUEUE_NAME", "llm_jobs"),
        celery_result_expires_seconds=env_int("CELERY_RESULT_EXPIRES_SECONDS", 86400),
    )
