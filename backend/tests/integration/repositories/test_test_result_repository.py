from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from competency_system.application.ports.repositories import TestResultInclude
from competency_system.domain.entities import (
    Candidate,
    Task,
    TaskCompetencyMapping,
    TestResult,
    Vacancy,
)
from competency_system.infrastructure.persistence.repositories import (
    CandidateRepository,
    CategoryRepository,
    TaskRepository,
    TestResultRepository,
    VacancyRepository,
)

from .helpers import build_taxonomy

pytestmark = pytest.mark.integration_repo


@pytest.mark.asyncio
async def test_test_result_repository_hydration_and_replacement(
    pg_session: AsyncSession,
) -> None:
    category_repo = CategoryRepository(pg_session)
    vacancy_repo = VacancyRepository(pg_session)
    candidate_repo = CandidateRepository(pg_session)
    task_repo = TaskRepository(pg_session)
    repo = TestResultRepository(pg_session)

    category, _, sub1, _ = build_taxonomy()
    await category_repo.add(category)

    vacancy = Vacancy(name="Backend", description="Role")
    await vacancy_repo.add(vacancy)

    candidate = Candidate(external_id="cand-result", vacancy_id=vacancy.id)
    await candidate_repo.add(candidate)

    task = Task(
        external_id="task-result",
        title="Result Task",
        competency_mappings=[
            TaskCompetencyMapping(sub_competency_id=sub1.id, weight=1.0)
        ],
    )
    await task_repo.add(task)

    result = TestResult(
        candidate_id=candidate.id,
        task_id=task.id,
        passed=True,
        score=90.0,
        question_answers=[{"question": "q1", "answer": "a1"}],
        llm_assessment={
            "passed": True,
            "score": 90.0,
            "feedback": "great",
            "criteria_version": "v1",
            "raw_test_score": 95.0,
            "penalized_test_score": 90.0,
            "attempt_penalty_applied": True,
            "final_score": 90.0,
            "strengths": ["structure"],
            "issues": ["none"],
        },
    )
    await repo.add(result)
    await pg_session.commit()

    loaded = await repo.get(
        result.id,
        include={TestResultInclude.QUESTION_ANSWERS, TestResultInclude.LLM_ASSESSMENT},
    )
    assert loaded is not None
    assert loaded.question_answers == [{"question": "q1", "answer": "a1"}]
    assert loaded.llm_assessment is not None
    assert loaded.llm_assessment["strengths"] == ["structure"]

    result.question_answers = [{"question": "q2", "answer": "a2"}]
    result.llm_assessment = None
    await repo.add(result)
    await pg_session.commit()

    updated = await repo.get(
        result.id,
        include={TestResultInclude.QUESTION_ANSWERS, TestResultInclude.LLM_ASSESSMENT},
    )
    assert updated is not None
    assert updated.question_answers == [{"question": "q2", "answer": "a2"}]
    assert updated.llm_assessment is None


@pytest.mark.asyncio
async def test_test_result_repository_fk_constraints(pg_session: AsyncSession) -> None:
    repo = TestResultRepository(pg_session)

    with pytest.raises(IntegrityError):
        await repo.add(TestResult(candidate_id=uuid4(), task_id=uuid4(), score=10.0))
