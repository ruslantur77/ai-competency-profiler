from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from competency_system.application.ports.repositories import CandidateInclude
from competency_system.infrastructure.persistence.repositories import (
    CandidateRepository,
)

pytestmark = pytest.mark.unit


def test_candidate_repository_load_options_for_vacancy_subcompetencies() -> None:
    repo = CandidateRepository(MagicMock())

    options = repo.load_options(include={CandidateInclude.VACANCY_SUBCOMPETENCIES})

    assert len(options) == 3


def test_candidate_repository_load_options_for_vacancy_only() -> None:
    repo = CandidateRepository(MagicMock())

    options = repo.load_options(include={CandidateInclude.VACANCY})

    assert len(options) == 1
