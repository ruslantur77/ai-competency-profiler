from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LMS
    lms_base_url: str
    lms_api_token: str

    # Наша система
    our_webhook_url: str
    our_webhook_secret: str = ""
    target_vacancy_id: str

    # Поллинг
    poll_interval_seconds: int = 3600
    initial_lookback_days: int = 1

    # БД
    db_path: str = "adapter_state.db"

    # Retry
    webhook_max_attempts: int = 5
    webhook_retry_min_wait: int = 2
    webhook_retry_max_wait: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()