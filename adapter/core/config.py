import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Адаптер
    adapter_port: int = 8001

    # Source (Kontest LMS)
    source_base_url: str          # http://91.229.9.49:8181/api/kontest
    source_api_token: str
    # CSV или JSON список course_id: "1,2,3" или "[1,2,3]"
    source_course_ids: str = "[]"

    # Маппинг course_id -> vacancy_id (JSON)
    # {"1": "40000000-0000-0000-0000-000000000001"}
    course_vacancy_map: str = "{}"

    # Backend (наша система)
    backend_webhook_url: str      # http://backend:8000/api/v1/webhook/task-completed
    backend_webhook_secret: str = ""

    # Поллинг
    poll_interval_seconds: int = 3600
    initial_lookback_minutes: int = 1440  # 24 часа

    # БД
    db_path: str = "adapter_state.db"

    # Retry / DLQ
    webhook_max_attempts: int = 5
    webhook_retry_min_wait: int = 2
    webhook_retry_max_wait: int = 60
    dlq_enabled: bool = True
    dlq_max_items_per_query: int = 100
    batch_size_outbox: int = 200

    # Прочее
    request_timeout_seconds: int = 60
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def get_course_ids(self) -> list[int]:
        """Парсит SOURCE_COURSE_IDS из CSV или JSON."""
        raw = self.source_course_ids.strip()
        try:
            # Пробуем JSON: "[1,2,3]"
            parsed = json.loads(raw)
            return [int(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
        # Пробуем CSV: "1,2,3"
        if raw:
            return [int(x.strip()) for x in raw.split(",") if x.strip()]
        return []

    def get_course_vacancy_map(self) -> dict[int, str]:
        """Парсит COURSE_VACANCY_MAP из JSON."""
        try:
            raw = json.loads(self.course_vacancy_map)
            return {int(k): v for k, v in raw.items()}
        except Exception:
            return {}

    def get_vacancy_id(self, course_id: int) -> str | None:
        """Возвращает vacancy_id для course_id."""
        return self.get_course_vacancy_map().get(course_id)


settings = Settings()