from datetime import datetime

from core.config import settings
from core.logging import logger
from lms.client import LmsClient
from pipeline.converter import (
    convert_case_to_external_task,
    convert_quiz_to_external_task,
)


async def get_external_tasks(
    start: datetime,
    end: datetime,
    force: bool = False,
) -> list[dict]:
    """
    Формирует список задач для бэкенда из LMS.
    Бэкенд вызывает этот эндпоинт через HTTPTestingSystemGateway.

    Берём:
    - cases из GET /integration/courses/{course_id} → course.cases
    - quizzes из GET /integration/courses/{course_id} → course.quizzes
    """
    lms_client = LmsClient()
    course_ids = settings.get_course_ids()

    if not course_ids:
        logger.warning("SOURCE_COURSE_IDS пустой — возвращаем пустой список")
        return []

    tasks = []
    seen_external_ids: set[str] = set()

    for course_id in course_ids:
        try:
            course = await lms_client.get_course_detail(course_id)
        except Exception as e:
            logger.error(
                f"Ошибка получения деталей course_id={course_id}: {e}"
            )
            continue

        # --- Code задачи (cases) ---
        for case in course.cases:
            # Фильтрация по временному окну (если не force)
            if not force and (case.created_at < start or case.created_at >= end):
                continue

            external_id = f"course_{course_id}_case_{case.case_id}"
            if external_id in seen_external_ids:
                continue
            seen_external_ids.add(external_id)

            tasks.append(
                convert_case_to_external_task(
                    course_id=course_id,
                    case=case,
                    created_at_iso=case.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )

        # --- Quiz задачи ---
        for quiz in course.quizzes:
            external_id = f"course_{course_id}_quiz_{quiz.lecture_id}"
            if external_id in seen_external_ids:
                continue
            seen_external_ids.add(external_id)

            tasks.append(
                convert_quiz_to_external_task(
                    course_id=course_id,
                    lecture_id=quiz.lecture_id,
                    title=quiz.title,
                    created_at_iso=quiz.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )

    logger.info(f"GET /external/tasks: сформировано {len(tasks)} задач")
    return tasks