from __future__ import annotations

from uuid import UUID

from competency_system.domain.entities.candidate import Candidate, CompetencyScore
from competency_system.domain.entities.competency import Competency
from competency_system.domain.entities.task import Task, TestResult


class CandidateScorer:
    """Сервис для оценки кандидата по результатам тестов."""

    def __init__(
        self,
        pass_threshold: float = 0.5,
        mapping_coverage_threshold: float = 0.2,
    ) -> None:
        """Args:
            pass_threshold: Минимальный normalized score для засчитывания
        """
        self.pass_threshold = pass_threshold
        self.mapping_coverage_threshold = mapping_coverage_threshold

    def calculate_achievements(
        self,
        test_results: list[TestResult],
        tasks: list[Task],
    ) -> set[UUID]:
        """Вычислить достигнутые subcompetencies из результатов тестов."""
        task_map: dict[UUID, Task] = {t.id: t for t in tasks}
        achieved: set[UUID] = set()

        for result in test_results:
            task = task_map.get(result.task_id)
            if not task:
                continue

            if result.normalized_score >= self.pass_threshold:
                for mapping in task.competency_mappings:
                    mapping_weight = min(max(mapping.weight, 0.0), 1.0)
                    coverage = result.normalized_score * mapping_weight
                    if coverage >= self.mapping_coverage_threshold:
                        achieved.add(mapping.sub_competency_id)

        return achieved

    def calculate_scores(
        self,
        candidate: Candidate,
        competencies: list[Competency],
    ) -> list[CompetencyScore]:
        """Рассчитать оценки по компетенциям для кандидата."""
        scores: list[CompetencyScore] = []

        for comp in competencies:
            level = comp.calculate_level(candidate.achieved_subcompetency_ids)
            total_weight = sum(
                min(max(sub.weight, 0.0), 1.0) for sub in comp.sub_competencies
            )
            achieved_weight = sum(
                min(max(sub.weight, 0.0), 1.0)
                for sub in comp.sub_competencies
                if sub.id in candidate.achieved_subcompetency_ids
            )
            confidence = (
                min(1.0, achieved_weight / total_weight) if total_weight > 0.0 else 0.0
            )

            scores.append(
                CompetencyScore(
                    competency_id=comp.id,
                    level=level,
                    confidence=confidence,
                )
            )

        return scores
