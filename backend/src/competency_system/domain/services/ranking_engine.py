from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from uuid import UUID

from competency_system.domain.entities.candidate import Candidate
from competency_system.domain.entities.vacancy import (
    Vacancy,
    VacancyCompetencyNode,
    VacancySubCompetencyNode,
)


@dataclass(frozen=True)
class RankingBreakdownItem:
    """Explainable contribution of a single competency to the final score."""

    competency_id: UUID
    competency_name: str
    required: bool
    matched_weight: float
    total_weight: float
    coverage: float
    score_contribution: float
    matched_subcompetency_ids: tuple[UUID, ...]
    total_subcompetency_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class RankingScore:
    """Результат ранжирования кандидата."""

    candidate_id: UUID
    candidate_external_id: str
    total_score: float  # 0-100
    required_match: float  # Доля покрытых обязательных компетенций
    desired_match: float  # Доля покрытых желательных компетенций
    required_score: float  # 0-100
    desired_score: float  # 0-100
    breakdown: tuple[RankingBreakdownItem, ...]


class RankingEngine:
    """Движок ранжирования на основе векторной близости."""

    def rank_candidates(
        self,
        vacancy: Vacancy,
        candidates: list[Candidate],
    ) -> list[RankingScore]:
        """Отранжировать кандидатов по подходимости к вакансии.

        Алгоритм:
        1. Разделить компетенции вакансии на обязательные и желательные.
        2. Для каждой компетенции посчитать cosine similarity между
           вектором весов вакансии и бинарным вектором достижений кандидата.
        3. Аггрегировать similarity обязательного и желательного блоков с
           весами 70/30 (или 100/0 и 0/100 для неполных групп).
        """
        if not vacancy.is_ready:
            raise ValueError("Vacancy must be ready")

        competency_nodes = list(vacancy.competency_nodes)
        sub_nodes = list(vacancy.sub_competency_nodes)
        if not competency_nodes:
            return []

        required_competencies = [node for node in competency_nodes if node.is_required]
        desired_competencies = [
            node for node in competency_nodes if not node.is_required
        ]
        required_total_weight = self._group_total_weight(
            required_competencies, sub_nodes
        )
        desired_total_weight = self._group_total_weight(desired_competencies, sub_nodes)
        required_budget, desired_budget = self._group_budgets(
            has_required=bool(required_competencies),
            has_desired=bool(desired_competencies),
        )

        scores: list[RankingScore] = []
        for candidate in candidates:
            breakdown = tuple(
                self._build_breakdown_item(
                    competency_node=competency,
                    sub_nodes=sub_nodes,
                    candidate=candidate,
                    group_budget=required_budget,
                    group_total_weight=required_total_weight,
                )
                for competency in required_competencies
            ) + tuple(
                self._build_breakdown_item(
                    competency_node=competency,
                    sub_nodes=sub_nodes,
                    candidate=candidate,
                    group_budget=desired_budget,
                    group_total_weight=desired_total_weight,
                )
                for competency in desired_competencies
            )

            required_match = self._group_similarity_ratio(breakdown, required=True)
            desired_match = self._group_similarity_ratio(breakdown, required=False)
            required_score = required_match * required_budget
            desired_score = desired_match * desired_budget
            total_score = required_score + desired_score

            scores.append(
                RankingScore(
                    candidate_id=candidate.id,
                    candidate_external_id=candidate.external_id,
                    total_score=total_score,
                    required_match=required_match,
                    desired_match=desired_match,
                    required_score=required_score,
                    desired_score=desired_score,
                    breakdown=breakdown,
                )
            )

        scores.sort(
            key=lambda score: (
                -score.total_score,
                -score.required_match,
                -score.desired_match,
                score.candidate_external_id,
            )
        )
        return scores

    def _build_breakdown_item(
        self,
        *,
        competency_node: VacancyCompetencyNode,
        sub_nodes: list[VacancySubCompetencyNode],
        candidate: Candidate,
        group_budget: float,
        group_total_weight: float,
    ) -> RankingBreakdownItem:
        competency = competency_node.competency
        if competency is None:
            raise ValueError(
                "Vacancy competency node must include competency reference"
            )
        scoped_sub_nodes = [
            node
            for node in sub_nodes
            if node.competency_id == competency_node.competency_id
        ]
        total_subcompetency_ids = tuple(
            node.sub_competency_id for node in scoped_sub_nodes
        )
        total_weight = self._competency_total_weight(scoped_sub_nodes)
        matched_subcompetency_ids = tuple(
            node.sub_competency_id
            for node in scoped_sub_nodes
            if node.sub_competency_id in candidate.achieved_subcompetency_ids
        )
        matched_weight = sum(
            self._clamp_weight(node.weight)
            for node in scoped_sub_nodes
            if node.sub_competency_id in candidate.achieved_subcompetency_ids
        )
        candidate_norm_sq = sum(
            1.0
            for node in scoped_sub_nodes
            if node.sub_competency_id in candidate.achieved_subcompetency_ids
        )
        vacancy_norm_sq = sum(
            self._clamp_weight(node.weight) ** 2 for node in scoped_sub_nodes
        )
        similarity = (
            matched_weight / (sqrt(vacancy_norm_sq) * sqrt(candidate_norm_sq))
            if vacancy_norm_sq > 0.0 and candidate_norm_sq > 0.0
            else 0.0
        )
        coverage = similarity
        score_contribution = (
            group_budget * (total_weight / group_total_weight) * similarity
            if group_budget > 0 and group_total_weight > 0 and total_weight > 0
            else 0.0
        )

        return RankingBreakdownItem(
            competency_id=competency.id,
            competency_name=competency.name,
            required=competency_node.is_required,
            matched_weight=matched_weight,
            total_weight=total_weight,
            coverage=coverage,
            score_contribution=score_contribution,
            matched_subcompetency_ids=matched_subcompetency_ids,
            total_subcompetency_ids=total_subcompetency_ids,
        )

    def _group_budgets(
        self, *, has_required: bool, has_desired: bool
    ) -> tuple[float, float]:
        if has_required and has_desired:
            return 70.0, 30.0
        if has_required:
            return 100.0, 0.0
        if has_desired:
            return 0.0, 100.0
        return 0.0, 0.0

    def _group_total_weight(
        self,
        competency_nodes: list[VacancyCompetencyNode],
        sub_nodes: list[VacancySubCompetencyNode],
    ) -> float:
        return sum(
            self._competency_total_weight(
                [
                    node
                    for node in sub_nodes
                    if node.competency_id == competency.competency_id
                ]
            )
            for competency in competency_nodes
        )

    def _group_similarity_ratio(
        self,
        breakdown: tuple[RankingBreakdownItem, ...],
        *,
        required: bool,
    ) -> float:
        group_items = [item for item in breakdown if item.required == required]
        if not group_items:
            return 1.0
        total_weight = sum(item.total_weight for item in group_items)
        if total_weight <= 0:
            return 0.0
        weighted_similarity = sum(
            item.total_weight * item.coverage for item in group_items
        )
        return weighted_similarity / total_weight

    def _competency_total_weight(
        self, scoped_sub_nodes: list[VacancySubCompetencyNode]
    ) -> float:
        return sum(self._clamp_weight(node.weight) for node in scoped_sub_nodes)

    def _clamp_weight(self, weight: float) -> float:
        return max(0.0, min(weight, 1.0))
