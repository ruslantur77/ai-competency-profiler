from __future__ import annotations

from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class TestDBSettings(BaseSettings):
    TEST_DB_HOST: str
    TEST_DB_PORT: int
    TEST_DB_NAME: str
    TEST_DB_USER: str
    TEST_DB_PASS: str

    model_config = SettingsConfigDict(env_file="tests/.env.test", extra="ignore")


@dataclass(frozen=True)
class ResolvedTestDBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    async_url: str
    sync_url: str

    @property
    def runtime_env(self) -> dict[str, str]:
        return {
            "DB_HOST": self.host,
            "DB_PORT": str(self.port),
            "DB_NAME": self.name,
            "DB_USER": self.user,
            "DB_PASS": self.password,
        }


def resolve_test_db_config() -> ResolvedTestDBConfig:
    settings = TestDBSettings()
    return ResolvedTestDBConfig(
        host=settings.TEST_DB_HOST,
        port=settings.TEST_DB_PORT,
        name=settings.TEST_DB_NAME,
        user=settings.TEST_DB_USER,
        password=settings.TEST_DB_PASS,
        async_url=(
            "postgresql+asyncpg://"
            f"{settings.TEST_DB_USER}:{settings.TEST_DB_PASS}@"
            f"{settings.TEST_DB_HOST}:{settings.TEST_DB_PORT}/{settings.TEST_DB_NAME}"
        ),
        sync_url=(
            "postgresql+psycopg2://"
            f"{settings.TEST_DB_USER}:{settings.TEST_DB_PASS}@"
            f"{settings.TEST_DB_HOST}:{settings.TEST_DB_PORT}/{settings.TEST_DB_NAME}"
        ),
    )
