import httpx

from core.config import settings
from core.logging import logger
from lms.schemas import LmsUserProgress


class LmsClient:
    """HTTP-клиент для получения прогресса из LMS другой команды."""

    def __init__(self) -> None:
        self._base_url = settings.lms_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.lms_api_token}",
            "Accept": "application/json",
        }

    async def get_user_progress(
        self,
        *,
        updated_from: str,
        updated_to: str,
        include_code: bool = True,
        include_content: bool = False,
    ) -> list[LmsUserProgress]:
        """
        Запрашивает прогресс пользователей за указанный период.

        Args:
            updated_from: ISO datetime строка начала периода (UTC)
            updated_to: ISO datetime строка конца периода (UTC)
            include_code: включать ли код сабмитов (для code-задач)
            include_content: включать ли контент лекций (нам не нужно)
        """
        params = {
            "updated_from": updated_from,
            "updated_to": updated_to,
            "include_code": str(include_code).lower(),
            "include_content": str(include_content).lower(),
        }

        url = f"{self._base_url}/integration/users/progress"
        logger.info(f"LMS запрос: GET {url} | период: {updated_from} → {updated_to}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()

        raw_list = response.json()
        logger.info(f"LMS вернул прогресс для {len(raw_list)} пользователей")

        return [LmsUserProgress.model_validate(item) for item in raw_list]