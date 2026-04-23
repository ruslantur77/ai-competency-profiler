from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from competency_system.application.dtos.task import CandidateTaskAssessmentDTO
from competency_system.application.ports.repositories import CandidateInclude
from competency_system.application.use_cases.candidate import CandidateScoringOperation
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import AssessmentStatus, TaskType
from tests.factories import TaskFactory, TaskSubCompetencyNodeFactory
from tests.fixtures.domain_graph import build_vacancy_with_graph

pytestmark = pytest.mark.integration_repo


async def test_candidate_scoring_operation_creates_candidate_before_test_result(
    uow_factory: Any,
) -> None:
    vacancy, category, competency, sub1, _ = build_vacancy_with_graph()
    task_external_id = "task-candidate-scoring-integration"
    task = TaskFactory().make(
        {
            "external_id": task_external_id,
            "sub_competency_nodes": [
                TaskSubCompetencyNodeFactory().make(
                    {
                        "task_id": uuid4(),
                        "sub_competency_id": sub1.id,
                        "competency_id": competency.id,
                        "weight": 1.0,
                    }
                )
            ],
        }
    )

    async with uow_factory() as uow:
        await uow.categories.add(category)
        await uow.vacancies.add(vacancy)
        await uow.tasks.add(task)
        await uow.commit()

    command = CandidateTaskAssessmentDTO(
        event_id="evt-candidate-scoring-integration",
        vacancy_id=vacancy.id,
        candidate_external_id="candidate-scoring-integration",
        task_external_id=task_external_id,
        type=TaskType.CODE,
        code="print('ok')",
        passed=1,
        total=1,
        attempts=1,
    )
    operation = CandidateScoringOperation(
        uow_factory(),
        CandidateScorer(),
        prompt_version="v1",
    )

    _, test_result, result_dto = await operation.run(command)

    async with uow_factory() as uow:
        saved_candidate = await uow.candidates.get_by_external_id(
            command.candidate_external_id,
            include={CandidateInclude.ACHIEVEMENTS},
        )
        saved_result = await uow.test_results.get(test_result.id)

    assert saved_candidate is not None
    assert saved_result is not None
    assert saved_result.candidate_id == saved_candidate.id
    assert saved_candidate.assessment_status == AssessmentStatus.COMPLETED
    assert saved_candidate.last_assessment_at is not None
    assert result_dto.candidate_profile.candidate_id == saved_candidate.id
