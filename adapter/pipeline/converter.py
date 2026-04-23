from datetime import datetime, timezone
from typing import Optional

from lms.schemas import LmsCase, LmsQuiz, LmsUserProgress
from competency.schemas import CandidateTaskAssessmentDTO
from core.config import settings
from core.logging import logger


def _build_case_event_id(user_id: int, case_id: int, submission_id: int) -> str:
    return f"case_{user_id}_{case_id}_{submission_id}"


def _build_quiz_event_id(user_id: int, lecture_id: int, attempts_used: int) -> str:
    return f"quiz_{user_id}_{lecture_id}_{attempts_used}"


def convert_case_to_event(
    user_id: int,
    case: LmsCase,
) -> Optional[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Конвертирует задачу с кодом (case) из LMS в DTO для нашего webhook.
    Возвращает (event_id, dto, raw_dict) или None если сабмитов нет
    или нет маппинга на вакансию.
    """
    if not case.submissions:
        return None

    # Ищем vacancy_id через маппинг
    task_external_id = str(case.case_id)
    vacancy_id = settings.get_vacancy_id(task_external_id)
    if not vacancy_id:
        logger.debug(
            f"Нет маппинга для case_id={case.case_id}, пропускаем"
        )
        return None

    # Берём последний сабмит по дате
    latest = max(case.submissions, key=lambda s: s.created_at)

    tests = latest.tests
    passed_count = sum(1 for t in tests if t.passed)
    total_count = len(tests) if tests else 1

    event_id = _build_case_event_id(user_id, case.case_id, latest.submission_id)

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
        "user_id": user_id,
        "case": case.model_dump(mode="json"),
        "selected_submission_id": latest.submission_id,
    }

    return event_id, dto, raw


def convert_quiz_to_event(
    user_id: int,
    quiz: LmsQuiz,
) -> Optional[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Конвертирует результат квиза (quiz) из LMS в DTO для нашего webhook.
    Возвращает None если нет попыток или нет маппинга на вакансию.
    """
    if quiz.attempts_used == 0:
        return None

    # Ищем vacancy_id через маппинг
    task_external_id = f"quiz_{quiz.lecture_id}"
    vacancy_id = settings.get_vacancy_id(task_external_id)
    if not vacancy_id:
        logger.debug(
            f"Нет маппинга для quiz lecture_id={quiz.lecture_id}, пропускаем"
        )
        return None

    event_id = _build_quiz_event_id(user_id, quiz.lecture_id, quiz.attempts_used)

    dto = CandidateTaskAssessmentDTO(
        event_id=event_id,
        vacancy_id=vacancy_id,
        candidate_external_id=str(user_id),
        task_external_id=task_external_id,
        type="test",
        passed=quiz.best_score or 0,
        total=quiz.max_score or 0,
        attempts=quiz.attempts_used,
    )

    raw = {
        "user_id": user_id,
        "quiz": quiz.model_dump(mode="json"),
    }

    return event_id, dto, raw


def extract_all_events(
    user_progress: LmsUserProgress,
) -> list[tuple[str, CandidateTaskAssessmentDTO, dict]]:
    """
    Извлекает все события из прогресса одного пользователя.
    Пропускает события без маппинга на вакансию.
    """
    user_id = user_progress.user.id
    events = []

    for case in user_progress.cases:
        result = convert_case_to_event(user_id, case)
        if result:
            events.append(result)

    for quiz in user_progress.quizzes:
        result = convert_quiz_to_event(user_id, quiz)
        if result:
            events.append(result)

    return events