from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.use_cases.candidate import CandidateScoringOperation
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import TaskType
from tests.factories import TaskFactory, TaskSubCompetencyMappingFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.unit


@pytest.fixture
def operation(mock_uow):
    return CandidateScoringOperation(mock_uow, CandidateScorer(), prompt_version="v1")


@pytest.fixture
def command() -> CandidateTaskAssessmentDTO:
    return CandidateTaskAssessmentDTO(
        event_id="evt-1",
        vacancy_id=uuid4(),
        candidate_external_id="candidate-1",
        task_external_id="task-1",
        type=TaskType.CODE,
        passed=1,
        total=1,
        attempts=1,
    )


async def test_candidate_scoring_operation_creates_result_and_candidate(
    operation: CandidateScoringOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    vacancy, _, _, sub1, _ = build_vacancy_with_graph()
    command.vacancy_id = vacancy.id
    task = TaskFactory().make(
        {
            "external_id": command.task_external_id,
            "sub_competency_mappings": [
                TaskSubCompetencyMappingFactory().make(
                    {"task_id": uuid4(), "sub_competency_id": sub1.id, "weight": 1.0}
                )
            ],
        }
    )
    mock_uow.candidates.get_by_external_id.return_value = None
    mock_uow.tasks.get_by_external_id.return_value = task
    mock_uow.vacancies.get.return_value = vacancy

    candidate, test_result, result = await operation.run(command)

    assert candidate.external_id == command.candidate_external_id
    assert test_result.task_id == task.id
    assert result.candidate_profile.candidate_id == candidate.id
    mock_uow.test_results.add.assert_awaited_once()
    mock_uow.candidates.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


async def test_candidate_scoring_operation_raises_when_task_not_found(
    operation: CandidateScoringOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.candidates.get_by_external_id.return_value = None
    mock_uow.tasks.get_by_external_id.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await operation.run(command)
