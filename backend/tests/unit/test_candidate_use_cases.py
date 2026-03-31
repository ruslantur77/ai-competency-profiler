from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.use_cases.candidate import (
    AssessCandidateUseCase,
    GetCandidateProfileUseCase,
)
from competency_system.domain.entities import (
    Candidate,
    Competency,
    SubCompetency,
    Task,
    TaskSubCompetencyMapping,
    TestResult,
    Vacancy,
    WebhookEvent,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.competency_level import CompetencyLevel
from competency_system.domain.value_objects.enums import (
    TaskType,
    VacancyStatus,
    WebhookEventStatus,
)

pytestmark = pytest.mark.unit


def test_candidate_scorer_uses_weighted_coverage() -> None:
    sub_critical = SubCompetency(name="Critical path", weight=0.7)
    sub_minor = SubCompetency(name="Minor path", weight=0.3)
    competency = Competency(
        category_id=UUID(int=1),
        name="API design",
        sub_competencies=[sub_critical, sub_minor],
    )
    candidate = Candidate(
        external_id="candidate-1",
        vacancy_id=uuid4(),
        achieved_subcompetency_ids={sub_critical.id},
    )

    scorer = CandidateScorer()
    scores = scorer.calculate_scores(candidate, [competency])

    assert len(scores) == 1
    assert scores[0].level == CompetencyLevel.ADVANCED
    assert scores[0].confidence == pytest.approx(0.7)


def test_candidate_scorer_requires_sufficient_result_quality() -> None:
    sub_critical = SubCompetency(name="Critical path", weight=0.8)
    sub_minor = SubCompetency(name="Minor path", weight=0.2)
    task = Task(
        external_id="task-1",
        title="Build API",
        description="Implement endpoint",
        type=TaskType.TEST,
        sub_competency_mappings=[
            TaskSubCompetencyMapping(sub_competency_id=sub_critical.id, weight=0.8),
            TaskSubCompetencyMapping(sub_competency_id=sub_minor.id, weight=0.2),
        ],
    )
    result = TestResult(
        candidate_id=uuid4(),
        task_id=task.id,
        passed=False,
        score=40.0,
        attempts=1,
    )

    scorer = CandidateScorer()
    achieved = scorer.calculate_achievements([result], [task])

    assert achieved == set()


@pytest.mark.asyncio
async def test_assess_candidate_marks_event_failed_when_task_not_found(mock_uow) -> None:
    vacancy_id = uuid4()
    command = CandidateTaskAssessmentDTO(
        event_id="event-1",
        vacancy_id=vacancy_id,
        candidate_external_id="candidate-1",
        task_external_id="task-404",
        type=TaskType.CODE,
        code="print('hello')",
        question_answers=[],
        passed=1,
        total=1,
        attempts=1,
        duration_seconds=10,
    )
    existing_processing_event = WebhookEvent(
        event_id=command.event_id,
        vacancy_id=vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSING,
        payload=command.model_dump(mode="json"),
    )
    mock_uow.webhook_events.get_by_event_id.side_effect = [
        None,
        existing_processing_event,
    ]
    mock_uow.candidates.get_by_external_id.return_value = None
    mock_uow.tasks.get_by_external_id.return_value = None

    use_case = AssessCandidateUseCase(mock_uow)

    with pytest.raises(ValueError, match="Task task-404 not found"):
        await use_case.execute(command)

    assert mock_uow.webhook_events.add.await_count == 2
    assert mock_uow.commit.await_count == 2


@pytest.mark.asyncio
async def test_get_candidate_profile_builds_scores_from_uow(mock_uow) -> None:
    sub_critical = SubCompetency(name="Critical path", weight=1.0)
    competency = Competency(
        category_id=UUID(int=1),
        name="API design",
        sub_competencies=[sub_critical],
    )
    vacancy = Vacancy(
        id=uuid4(),
        name="Backend Engineer",
        description="Build APIs",
        status=VacancyStatus.READY,
        competencies=[competency],
    )
    candidate = Candidate(
        id=uuid4(),
        external_id="candidate-1",
        vacancy_id=vacancy.id,
        achieved_subcompetency_ids={sub_critical.id},
    )
    mock_uow.candidates.get.return_value = candidate
    mock_uow.vacancies.get.return_value = vacancy

    result = await GetCandidateProfileUseCase(mock_uow).execute(candidate.id)

    assert result.candidate_id == candidate.id
    assert result.external_id == "candidate-1"
    assert result.total_score == pytest.approx(100.0)
