import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger


class TaskNotSyncedError(Exception):
    """Таск ещё не синкнут — оставляем pending."""
    pass


class WebhookConfigError(Exception):
    """Конфигурационная ошибка (401/403) — сразу в DLQ."""
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
    """HTTP-клиент для отправки результатов в наш webhook."""

    def __init__(self) -> None:
        self._webhook_url = settings.backend_webhook_url
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.backend_webhook_secret:
            self._headers["X-Webhook-Secret"] = settings.backend_webhook_secret

    async def send_assessment(
        self,
        dto: CandidateTaskAssessmentDTO,
        http_client: httpx.AsyncClient,
    ) -> None:
        """
        Отправляет событие в webhook.

        Коды ответа:
          2xx  — успех
          409  — уже обработано, считаем успехом
          404/422 — таск не синкнут → TaskNotSyncedError (остаётся pending)
          401/403 — проблема с секретом → WebhookConfigError (сразу DLQ)
          остальные 4xx/5xx — retry
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

            if response.status_code == 409:
                logger.info(
                    f"event_id={dto.event_id} уже обработан (409), успех"
                )
                return

            if response.status_code in (404, 422):
                raise TaskNotSyncedError(
                    f"event_id={dto.event_id} task={dto.task_external_id} "
                    f"не найден (HTTP {response.status_code}): {response.text[:200]}"
                )

            if response.status_code in (401, 403):
                raise WebhookConfigError(
                    f"Ошибка авторизации webhook (HTTP {response.status_code}), "
                    f"проверьте BACKEND_WEBHOOK_SECRET"
                )

            response.raise_for_status()

        await _do_send()
        logger.info(f"Webhook отправлен: event_id={dto.event_id}")