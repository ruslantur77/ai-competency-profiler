from __future__ import annotations

from uuid import uuid4

import pytest

from competency_system.domain.entities import (
    SubCompetency,
    Task,
    TaskSubCompetencyMapping,
    TestResult,
)
from competency_system.domain.services.candidate_scorer import CandidateScorer
from competency_system.domain.value_objects.enums import (
    TaskType,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xfail(reason="Legacy use-case tests pending rewrite"),
]


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
