from __future__ import annotations

import pytest

pytest.importorskip("airflow")

from competency_system.presentation.airflow.dags.candidate_assessment import (
    candidate_assessment,
)
from competency_system.presentation.airflow.dags.ranking_recalculation import (
    ranking_recalculation,
)
from competency_system.presentation.airflow.dags.task_sync import task_sync
from competency_system.presentation.airflow.dags.vacancy_extraction import (
    vacancy_extraction,
)


def test_airflow_dag_ids() -> None:
    assert vacancy_extraction.dag_id == "vacancy_extraction"
    assert task_sync.dag_id == "task_sync"
    assert candidate_assessment.dag_id == "candidate_assessment"
    assert ranking_recalculation.dag_id == "ranking_recalculation"


def test_airflow_dag_task_counts() -> None:
    assert len(vacancy_extraction.tasks) == 1
    assert len(task_sync.tasks) == 1
    assert len(candidate_assessment.tasks) == 2
    assert len(ranking_recalculation.tasks) == 1
