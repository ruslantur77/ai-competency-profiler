import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LMS
    lms_base_url: str
    lms_api_token: str

    # Наша система
    our_webhook_url: str
    our_webhook_secret: str = ""

    # Маппинг: JSON строка вида {"case_27": "uuid-вакансии", "quiz_2": "uuid-вакансии"}
    # Ключи: "case_{case_id}" или "quiz_{lecture_id}"
    course_vacancy_mapping: str = "{}"

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

    def get_vacancy_id(self, task_external_id: str) -> str | None:
        """
        Возвращает vacancy_id для задачи по task_external_id.
        task_external_id: "27" (case) или "quiz_2" (quiz)
        """
        try:
            mapping: dict = json.loads(self.course_vacancy_mapping)
        except Exception:
            return None
        return mapping.get(task_external_id)


settings = Settings()