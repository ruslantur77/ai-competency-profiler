from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm.attributes import set_committed_value

from competency_system.domain.entities import Candidate, Vacancy
from competency_system.infrastructure.persistence.mappers import _load_all
from competency_system.infrastructure.persistence.models import (
    AssessmentStatus,
    CandidateOrm,
    VacancyOrm,
    VacancyStatus,
)

pytestmark = pytest.mark.unit


def make_candidate(
    *,
    load_vacancy: bool = False,
    load_achievements: bool = False,
    load_test_results: bool = False,
) -> CandidateOrm:
    candidate = CandidateOrm(
        id=uuid4(),
        external_id="ext-123",
        vacancy_id=uuid4(),
        status=AssessmentStatus.PENDING,
        last_assessment_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    if load_vacancy:
        vacancy = VacancyOrm(
            id=candidate.vacancy_id,
            name="Backend Engineer",
            description="Build APIs",
            status=VacancyStatus.READY,
        )
        set_committed_value(candidate, "vacancy", vacancy)
    if load_achievements:
        set_committed_value(candidate, "achievements", [])
    if load_test_results:
        set_committed_value(candidate, "test_results", [])
    return candidate


class TestLoadAll:
    def test_loads_scalar_fields_only(self):
        candidate = make_candidate()

        result = _load_all(candidate, Candidate)

        assert isinstance(result, Candidate)
        assert result.external_id == "ext-123"
        assert result.status == AssessmentStatus.PENDING
        assert result.last_assessment_at is None
        assert result.vacancy is None
        assert result.achievements == []

    def test_loads_with_vacancy(self):
        candidate = make_candidate(load_vacancy=True)

        result = _load_all(candidate, Candidate)

        assert result.vacancy is not None
        assert isinstance(result.vacancy, Vacancy)

    def test_loads_with_empty_achievements(self):
        candidate = make_candidate(load_achievements=True)

        result = _load_all(candidate, Candidate)

        assert result.achievements == []

    def test_raises_for_non_orm(self):
        with pytest.raises(ValueError, match="only orm models"):
            _load_all(MagicMock(spec=[]), Candidate)

    def test_raises_for_non_dataclass_domain(self):
        candidate = make_candidate()

        class NotADataclass:
            def __init__(self, **kwargs):
                pass

        with pytest.raises(TypeError, match="domain_model must be a dataclass"):
            _load_all(candidate, NotADataclass)

    def test_all_relationships_loaded(self):
        candidate = make_candidate(
            load_vacancy=True,
            load_achievements=True,
            load_test_results=True,
        )

        result = _load_all(candidate, Candidate)

        assert result.vacancy is not None
        assert isinstance(result.achievements, list)
        assert isinstance(result.test_results, list)
