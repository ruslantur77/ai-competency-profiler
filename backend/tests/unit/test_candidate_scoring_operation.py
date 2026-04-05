# ruff: noqa: E501
from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import (
    CandidateTaskAssessmentDTO,
    LLMCodeAssessmentDTO,
    LLMFeedbackItemDTO,
)
from competency_system.application.use_cases.candidate import CandidateScoringOperation
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import LLMFeedbackType, TaskType
from tests.factories import (
    CandidateFactory,
    TaskFactory,
    TaskSubCompetencyMappingFactory,
    TestResultFactory,
    TestResultLLMAssessmentFactory,
)
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


async def test_candidate_scoring_operation_raises_on_candidate_vacancy_mismatch(
    operation: CandidateScoringOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    other_vacancy_id = uuid4()
    command.vacancy_id = uuid4()
    mock_uow.candidates.get_by_external_id.return_value = CandidateFactory().make(
        {"vacancy_id": other_vacancy_id}
    )

    with pytest.raises(ValueError, match="another vacancy"):
        await operation.run(command)


async def test_candidate_scoring_operation_raises_when_vacancy_not_found(
    operation: CandidateScoringOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    task = TaskFactory().make({"external_id": command.task_external_id})
    mock_uow.candidates.get_by_external_id.return_value = None
    mock_uow.tasks.get_by_external_id.return_value = task
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="Vacancy"):
        await operation.run(command)


async def test_candidate_scoring_operation_apply_llm_assessment_noops_when_missing_result(
    operation: CandidateScoringOperation, mock_uow
) -> None:
    mock_uow.test_results.get.return_value = None

    await operation.apply_llm_assessment(
        uuid4(),
        LLMCodeAssessmentDTO(
            passed=True,
            score=70.0,
            feedback_items=[
                LLMFeedbackItemDTO(type=LLMFeedbackType.POSITIVE, value="ok")
            ],
        ),
    )

    mock_uow.test_results.add.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


async def test_candidate_scoring_operation_apply_llm_assessment_updates_existing_assessment(
    operation: CandidateScoringOperation, mock_uow
) -> None:
    existing_assessment = TestResultLLMAssessmentFactory().make(
        {"raw_test_score": 80.0, "penalized_test_score": 72.0}
    )
    result = TestResultFactory().make(
        {
            "attempts": 2,
            "score": 60.0,
            "llm_assessment": existing_assessment,
        }
    )
    mock_uow.test_results.get.return_value = result
    assessment = LLMCodeAssessmentDTO(
        passed=True,
        score=75.0,
        feedback="better",
        feedback_items=[
            LLMFeedbackItemDTO(type=LLMFeedbackType.POSITIVE, value="clean")
        ],
    )

    await operation.apply_llm_assessment(result.id, assessment)

    assert result.score == 75.0
    assert result.passed is True
    assert result.llm_assessment is not None
    assert result.llm_assessment.raw_test_score == 80.0
    assert result.llm_assessment.penalized_test_score == 72.0
    assert result.llm_assessment.feedback_items[0].position == 0
    mock_uow.test_results.add.assert_awaited_once_with(result)
    mock_uow.commit.assert_awaited_once()


async def test_candidate_scoring_operation_reuses_existing_candidate_for_same_vacancy(
    operation: CandidateScoringOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    vacancy, _, _, sub1, _ = build_vacancy_with_graph()
    command.vacancy_id = vacancy.id
    existing_candidate = CandidateFactory().make({"vacancy_id": vacancy.id})
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
    mock_uow.candidates.get_by_external_id.return_value = existing_candidate
    mock_uow.tasks.get_by_external_id.return_value = task
    mock_uow.vacancies.get.return_value = vacancy

    candidate, _, _ = await operation.run(command)

    assert candidate.id == existing_candidate.id


def test_candidate_scoring_operation_raw_score_returns_zero_for_non_positive_total() -> (
    None
):
    assert CandidateScoringOperation._raw_score(3, 0) == 0.0
