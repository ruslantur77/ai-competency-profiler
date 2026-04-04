from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.dtos.webhooks import WebhookEvent, WebhookEventStatus
from competency_system.application.use_cases.candidate import (
    WebhookEventOperation,
    _DuplicateWebhookEvent,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import TaskType
from tests.factories import CandidateFactory, TestResultFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def operation(mock_uow):
    return WebhookEventOperation(mock_uow, CandidateScorer())


@pytest.fixture
def command() -> CandidateTaskAssessmentDTO:
    return CandidateTaskAssessmentDTO(
        event_id="evt-1",
        vacancy_id=uuid4(),
        candidate_external_id="candidate-1",
        task_external_id="task-1",
        type=TaskType.CODE,
    )


async def test_webhook_event_operation_creates_processing_event(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.webhook_events.get_by_event_id.return_value = None

    await operation.ensure_processing(command)

    mock_uow.webhook_events.add.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


async def test_webhook_event_operation_rejects_processing_duplicate(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.webhook_events.get_by_event_id.return_value = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSING,
    )

    with pytest.raises(ValueError, match="is processing"):
        await operation.ensure_processing(command)


async def test_webhook_event_operation_rejects_already_handled_event(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.webhook_events.get_by_event_id.return_value = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.FAILED,
    )

    with pytest.raises(ValueError, match="already handled"):
        await operation.ensure_processing(command)


async def test_webhook_event_operation_replays_processed_duplicate_result(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    candidate = CandidateFactory().make({"vacancy_id": command.vacancy_id})
    test_result = TestResultFactory().make({"candidate_id": candidate.id})
    event = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSED,
        candidate_id=candidate.id,
        test_result_id=test_result.id,
    )
    vacancy = type("VacancyLike", (), {"requirement_competencies": []})()
    mock_uow.webhook_events.get_by_event_id.return_value = event
    mock_uow.candidates.get.return_value = candidate
    mock_uow.test_results.get.return_value = test_result
    mock_uow.vacancies.get.return_value = vacancy

    with pytest.raises(_DuplicateWebhookEvent) as exc:
        await operation.ensure_processing(command)

    assert exc.value.result.candidate_profile.candidate_id == candidate.id
    mock_uow.commit.assert_not_awaited()


async def test_webhook_event_operation_mark_processed_updates_existing_event(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    event = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSING,
    )
    candidate_id = uuid4()
    result_id = uuid4()
    mock_uow.webhook_events.get_by_event_id.return_value = event

    await operation.mark_processed(
        command, candidate_id=candidate_id, test_result_id=result_id
    )

    assert event.status == WebhookEventStatus.PROCESSED
    assert event.candidate_id == candidate_id
    assert event.test_result_id == result_id
    mock_uow.webhook_events.add.assert_awaited_once_with(event)
    mock_uow.commit.assert_awaited_once()


async def test_webhook_event_operation_mark_failed_noops_when_event_missing(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.webhook_events.get_by_event_id.return_value = None

    await operation.mark_failed(command, "boom")

    mock_uow.webhook_events.add.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


async def test_webhook_event_operation_rejects_processed_event_with_missing_references(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    mock_uow.webhook_events.get_by_event_id.return_value = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSED,
        candidate_id=None,
        test_result_id=uuid4(),
    )

    with pytest.raises(ValueError, match="missing result"):
        await operation.ensure_processing(command)


async def test_webhook_event_operation_rejects_processed_event_with_missing_entities(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    event = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSED,
        candidate_id=uuid4(),
        test_result_id=uuid4(),
    )
    mock_uow.webhook_events.get_by_event_id.return_value = event
    mock_uow.candidates.get.return_value = None
    mock_uow.test_results.get.return_value = None

    with pytest.raises(ValueError, match="missing result"):
        await operation.ensure_processing(command)


async def test_webhook_event_operation_rejects_when_vacancy_not_found(
    operation: WebhookEventOperation, mock_uow, command: CandidateTaskAssessmentDTO
) -> None:
    candidate = CandidateFactory().make({"vacancy_id": command.vacancy_id})
    test_result = TestResultFactory().make({"candidate_id": candidate.id})
    event = WebhookEvent(
        id=uuid4(),
        event_id=command.event_id,
        vacancy_id=command.vacancy_id,
        candidate_external_id=command.candidate_external_id,
        task_external_id=command.task_external_id,
        status=WebhookEventStatus.PROCESSED,
        candidate_id=candidate.id,
        test_result_id=test_result.id,
    )
    mock_uow.webhook_events.get_by_event_id.return_value = event
    mock_uow.candidates.get.return_value = candidate
    mock_uow.test_results.get.return_value = test_result
    mock_uow.vacancies.get.return_value = None

    with pytest.raises(ValueError, match="Vacancy"):
        await operation.ensure_processing(command)
