from __future__ import annotations

import pytest

from competency_system.domain.services.ranking_engine import RankingEngine

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xfail(reason="Legacy use-case tests pending rewrite"),
]


def test_ranking_engine_separates_required_and_desired_groups() -> None:
    vacancy, candidates = _build_ranking_fixture()

    scores = RankingEngine().rank_candidates(vacancy, candidates)

    assert [score.candidate_external_id for score in scores] == [
        "candidate-full",
        "candidate-required-only",
        "candidate-desired-only",
    ]
    top = scores[0]
    assert top.required_score == pytest.approx(64.34015210126405)
    assert top.desired_score == pytest.approx(30.0)
    assert top.total_score == pytest.approx(94.34015210126405)
