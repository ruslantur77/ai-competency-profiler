import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger


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
        Retry с exponential backoff настраивается через .env.
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
            response.raise_for_status()

        await _do_send()
        logger.info(f"Webhook отправлен: event_id={dto.event_id}")