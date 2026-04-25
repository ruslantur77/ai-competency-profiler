from typing import Optional

from lms.schemas import LmsCaseProgress, LmsQuiz, LmsUserProgress, LmsCaseRef
from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger


# --- Формирование составных ID ---

def build_case_task_external_id(course_id: int, case_id: int) -> str:
    """course_{course_id}_case_{case_id}"""
    return f"course_{course_id}_case_{case_id}"


def build_quiz_task_external_id(course_id: int, lecture_id: int) -> str:
    """course_{course_id}_quiz_{lecture_id}"""
    return f"course_{course_id}_quiz_{lecture_id}"


def build_case_event_id(
    course_id: int, case_id: int, user_id: int, submission_id: int
) -> str:
    """course_{course_id}_case_{case_id}_user_{user_id}_submission_{submission_id}"""
    return f"course_{course_id}_case_{case_id}_user_{user_id}_submission_{submission_id}"


def build_quiz_event_id(
    course_id: int, lecture_id: int, user_id: int, attempts_used: int
) -> str:
    """course_{course_id}_quiz_{lecture_id}_user_{user_id}_attempt_{attempts_used}"""
    return f"course_{course_id}_quiz_{lecture_id}_user_{user_id}_attempt_{attempts_used}"


# --- Конвертация ---

def convert_case_to_event(
    course_id: int,
    user_id: int,
    case: LmsCaseProgress,
    vacancy_id: str,
) -> Optional[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Конвертирует code-задачу (case) в DTO для webhook.
    Берём последний submission — политика "только последняя попытка".
    """
    if not case.submissions:
        return None

    latest = max(case.submissions, key=lambda s: s.created_at)

    tests = latest.tests
    passed_count = sum(1 for t in tests if t.passed)
    total_count = len(tests) if tests else 1

    task_external_id = build_case_task_external_id(course_id, case.case_id)
    event_id = build_case_event_id(
        course_id, case.case_id, user_id, latest.submission_id
    )

    dto = CandidateTaskAssessmentDTO(
        event_id=event_id,
        vacancy_id=vacancy_id,
        candidate_external_id=str(user_id),
        task_external_id=task_external_id,
        type="code",
        code=latest.code,
        passed=passed_count,
        total=total_count,
        attempts=case.attempts_count,
        duration_seconds=(latest.total_time_ms or 0) // 1000,
    )

    raw = {
        "course_id": course_id,
        "user_id": user_id,
        "case_id": case.case_id,
        "selected_submission_id": latest.submission_id,
    }

    return event_id, dto, raw


def convert_quiz_to_event(
    course_id: int,
    user_id: int,
    quiz: LmsQuiz,
    vacancy_id: str,
) -> Optional[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Конвертирует квиз в DTO для webhook.
    Берём best_score — политика "только последняя попытка".
    """
    if quiz.attempts_used == 0:
        return None

    task_external_id = build_quiz_task_external_id(course_id, quiz.lecture_id)
    event_id = build_quiz_event_id(
        course_id, quiz.lecture_id, user_id, quiz.attempts_used
    )

    dto = CandidateTaskAssessmentDTO(
        event_id=event_id,
        vacancy_id=vacancy_id,
        candidate_external_id=str(user_id),
        task_external_id=task_external_id,
        type="test",
        passed=quiz.best_score or 0,
        total=quiz.max_score or 0,
        attempts=quiz.attempts_used,
        question_answers=[],  # v1: пустой массив
    )

    raw = {
        "course_id": course_id,
        "user_id": user_id,
        "lecture_id": quiz.lecture_id,
    }

    return event_id, dto, raw


def extract_all_events(
    course_id: int,
    user_progress: LmsUserProgress,
    vacancy_id: str,
) -> list[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Извлекает все события из прогресса одного пользователя для одного курса.
    """
    user_id = user_progress.user.id
    events = []

    for case in user_progress.cases:
        result = convert_case_to_event(course_id, user_id, case, vacancy_id)
        if result:
            events.append(result)

    for quiz in user_progress.quizzes:
        result = convert_quiz_to_event(course_id, user_id, quiz, vacancy_id)
        if result:
            events.append(result)

    return events


# --- Конвертация задач для GET /external/tasks ---

def convert_case_to_external_task(
    course_id: int,
    case: LmsCaseRef,   # ← было LmsCase, теперь LmsCaseRef
    created_at_iso: str,
) -> dict:
    return {
        "external_id": build_case_task_external_id(course_id, case.case_id),  # ← было case.id
        "title": case.title,
        "description": case.description or "",
        "type": "code",
        "tags": [f"course:{course_id}", "kind:case"],
        "created_at": created_at_iso,
    }


def convert_quiz_to_external_task(
    course_id: int,
    lecture_id: int,
    title: str,
    created_at_iso: str,
) -> dict:
    """Конвертирует quiz (lecture) в формат ExternalTask для бэкенда."""
    return {
        "external_id": build_quiz_task_external_id(course_id, lecture_id),
        "title": f"Quiz: {title}",
        "description": f"Автосгенерированная задача по квизу lecture {lecture_id}",
        "type": "test",
        "tags": [f"course:{course_id}", "kind:quiz"],
        "created_at": created_at_iso,
    }