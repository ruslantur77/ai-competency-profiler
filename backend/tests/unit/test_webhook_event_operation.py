from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.dtos.webhooks import WebhookEvent, WebhookEventStatus
from competency_system.application.use_cases.candidate import WebhookEventOperation
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import TaskType

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
