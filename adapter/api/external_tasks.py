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
    - cases из GET /courses/{course_id}/cases
    - quizzes из /users/progress (уникальные lecture_id)

    Фильтрация по start/end — по created_at для cases.
    Для quizzes created_at не знаем — отдаём все из курса.
    """
    lms_client = LmsClient()
    course_ids = settings.get_course_ids()

    if not course_ids:
        logger.warning("SOURCE_COURSE_IDS пустой — возвращаем пустой список задач")
        return []

    tasks = []
    seen_external_ids = set()

    for course_id in course_ids:
        # --- Code задачи (cases) ---
        try:
            cases = await lms_client.get_course_cases(course_id)
        except Exception as e:
            logger.error(
                f"Ошибка получения cases для course_id={course_id}: {e}"
            )
            cases = []

        for case in cases:
            # Фильтруем по временному окну
            if case.created_at < start or case.created_at >= end:
                if not force:
                    continue

            external_id = f"course_{course_id}_case_{case.id}"
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

        # --- Quiz задачи (из прогресса — берём уникальные lecture_id) ---
        try:
            all_progress = await lms_client.get_user_progress(
                updated_from=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                updated_to=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        except Exception as e:
            logger.error(
                f"Ошибка получения прогресса для course_id={course_id}: {e}"
            )
            all_progress = []

        seen_quizzes: set[int] = set()
        for user_progress in all_progress:
            for quiz in user_progress.quizzes:
                if quiz.lecture_id in seen_quizzes:
                    continue
                seen_quizzes.add(quiz.lecture_id)

                external_id = f"course_{course_id}_quiz_{quiz.lecture_id}"
                if external_id in seen_external_ids:
                    continue
                seen_external_ids.add(external_id)

                # Берём название из lectures если есть
                title = f"Lecture {quiz.lecture_id}"
                for lecture in user_progress.lectures:
                    if lecture.lecture_id == quiz.lecture_id:
                        title = lecture.title
                        break

                tasks.append(
                    convert_quiz_to_external_task(
                        course_id=course_id,
                        lecture_id=quiz.lecture_id,
                        title=title,
                        created_at_iso=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    )
                )

    logger.info(f"GET /external/tasks: сформировано {len(tasks)} задач")
    return tasks