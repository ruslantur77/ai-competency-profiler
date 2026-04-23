import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger


class TaskNotSyncedError(Exception):
    """
    Таск ещё не синкнут в нашей системе.
    Событие надо оставить pending и попробовать позже.
    """
    pass


def _make_retry_decorator():
    return retry(
        stop=stop_after_attempt(settings.webhook_max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=settings.webhook_retry_min_wait,
            max=settings.webhook_retry_max_wait,
        ),
        reraise=True,
    )


class CompetencyClient:
    """HTTP-клиент для отправки результатов в нашу систему."""

    def __init__(self) -> None:
        self._webhook_url = settings.our_webhook_url
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.our_webhook_secret:
            self._headers["X-Webhook-Secret"] = settings.our_webhook_secret

    async def send_assessment(
        self,
        dto: CandidateTaskAssessmentDTO,
        http_client: httpx.AsyncClient,
    ) -> None:
        """
        Отправляет одно событие в webhook нашей системы.

        Коды ответа:
          2xx  - успех
          409  - событие уже обработано, считаем успехом (идемпотентность)
          404  - таск не найден (ещё не синкнут Airflow) → TaskNotSyncedError
          422  - таск не прошёл валидацию (скорее всего тоже не синкнут) → TaskNotSyncedError
          остальные 4xx/5xx - настоящая ошибка, будет retry
        """
        retry_decorator = _make_retry_decorator()

        @retry_decorator
        async def _do_send():
            logger.debug(f"Отправка webhook: event_id={dto.event_id}")
            response = await http_client.post(
                self._webhook_url,
                json=dto.model_dump(),
                headers=self._headers,
                timeout=30.0,
            )

            # Уже обработано — считаем успехом
            if response.status_code == 409:
                logger.info(
                    f"event_id={dto.event_id} уже обработан (409), считаем успехом"
                )
                return

            # Таск не найден в нашей системе — Airflow ещё не синкнул.
            # Пробрасываем специальный exception — retry не нужен,
            # попробуем в следующем цикле поллинга.
            if response.status_code in (404, 422):
                body = response.text[:300]
                raise TaskNotSyncedError(
                    f"event_id={dto.event_id} task_external_id={dto.task_external_id} "
                    f"не найден в системе (HTTP {response.status_code}): {body}"
                )

            # Всё остальное кроме 2xx — бросаем исключение → retry
            response.raise_for_status()

        await _do_send()
        logger.info(f"Webhook отправлен: event_id={dto.event_id}")