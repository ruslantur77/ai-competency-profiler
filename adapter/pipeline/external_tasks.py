from datetime import datetime, timezone
import aiosqlite
from core.config import settings
from core.logging import logger
from lms.client import LmsClient
from pipeline.converter import (
    convert_case_to_external_task,
    convert_quiz_to_external_task,
)

async def _cache_tasks(tasks: list[dict]) -> None:
    """Сохраняем задачи в локальный кэш."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(settings.db_path) as db:
        for task in tasks:
            # Извлекаем course_id из external_id (course_1_case_1 → 1)
            parts = task["external_id"].split("_")
            course_id = int(parts[1])

            await db.execute(
                """
                INSERT OR REPLACE INTO course_cache
                    (course_id, external_id, task_type, title, description, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    task["external_id"],
                    task["type"],
                    task["title"],
                    task.get("description", ""),
                    now,
                ),
            )
        await db.commit()


async def get_external_tasks(
    start: datetime,
    end: datetime,
    force: bool = False,
) -> list[dict]:
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
            logger.error(f"Ошибка получения деталей course_id={course_id}: {e}")
            continue

        # --- Code задачи (cases) ---
        for case in course.cases:
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

        # --- Quiz задачи — теперь дёргаем детали по slug ---
        for quiz in course.quizzes:
            external_id = f"course_{course_id}_quiz_{quiz.lecture_id}"
            if external_id in seen_external_ids:
                continue
            seen_external_ids.add(external_id)

            # Получаем детали квиза по slug
            try:
                quiz_detail = await lms_client.get_quiz_detail(quiz.slug)
            except Exception as e:
                logger.warning(
                    f"Не удалось получить детали квиза slug={quiz.slug}, "
                    f"используем базовые данные: {e}"
                )
                # Fallback — используем базовые данные из course detail
                tasks.append({
                    "external_id": external_id,
                    "title": f"Quiz: {quiz.title}",
                    "description": quiz.description or "",
                    "type": "test",
                    "tags": [f"course:{course_id}", "kind:quiz"],
                    "created_at": quiz.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                continue

            tasks.append(
                convert_quiz_to_external_task(
                    course_id=course_id,
                    quiz_detail=quiz_detail,
                    created_at_iso=quiz.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )

    logger.info(f"GET /external/tasks: сформировано {len(tasks)} задач")

    try:
        await _cache_tasks(tasks)
        logger.info(f"Кэш обновлён: {len(tasks)} задач")
    except Exception as e:
        logger.error(f"Ошибка кэширования задач: {e}", exc_info=True)

    return tasks