import httpx

from core.config import settings
from core.logging import logger
from lms.schemas import LmsUserProgress, LmsCourse, LmsCase


class LmsClient:
    """HTTP-клиент для Kontest LMS."""

    def __init__(self) -> None:
        self._base_url = settings.source_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.source_api_token}",
            "Accept": "application/json",
        }
        self._timeout = settings.request_timeout_seconds

    async def get_my_courses(self) -> list[LmsCourse]:
        """GET /courses/my — список курсов."""
        url = f"{self._base_url}/courses/my"
        logger.info(f"LMS запрос: GET {url}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()

        data = response.json()
        logger.info(f"LMS вернул {len(data)} курсов")
        return [LmsCourse.model_validate(item) for item in data]

    async def get_course_cases(self, course_id: int) -> list[LmsCase]:
        """GET /courses/{course_id}/cases — справочник code-задач курса."""
        url = f"{self._base_url}/courses/{course_id}/cases"
        logger.info(f"LMS запрос: GET {url}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()

        data = response.json()
        logger.info(f"LMS вернул {len(data)} cases для course_id={course_id}")
        return [LmsCase.model_validate(item) for item in data]

    async def get_user_progress(
        self,
        *,
        updated_from: str,
        updated_to: str,
        include_code: bool = True,
        include_content: bool = False,
    ) -> list[LmsUserProgress]:
        """GET /integration/users/progress — прогресс пользователей."""
        params = {
            "updated_from": updated_from,
            "updated_to": updated_to,
            "include_code": str(include_code).lower(),
            "include_content": str(include_content).lower(),
        }
        url = f"{self._base_url}/integration/users/progress"
        logger.info(
            f"LMS запрос: GET {url} | период: {updated_from} → {updated_to}"
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()

        data = response.json()
        logger.info(f"LMS вернул прогресс для {len(data)} пользователей")
        return [LmsUserProgress.model_validate(item) for item in data]