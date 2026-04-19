from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from competency_system.application.dtos.candidate import (
    CandidateProfileDTO,
    CompetencyScoreDTO,
)
from competency_system.application.dtos.ranking import (
    RankingBreakdownItemDTO,
    RankingItemDTO,
)
from competency_system.application.dtos.task import (
    TaskCategoryNodeDTO,
    TaskCompetencyNodeDTO,
    TaskDTO,
    TaskListItemDTO,
    TaskSubCompetencyNodeDTO,
    TestResultDTO,
)
from competency_system.application.dtos.vacancy import (
    VacancyCategoryNodeDTO,
    VacancyCompetencyNodeDTO,
    VacancyDTO,
    VacancyGraphSuggestionDTO,
    VacancyListItemDTO,
    VacancySubCompetencyNodeDTO,
)
from competency_system.domain.entities import (
    Candidate,
    Competency,
    CompetencyScore,
    Task,
    TestResult,
    Vacancy,
    VacancyGraphSuggestion,
)
from competency_system.domain.services.ranking_engine import (
    RankingBreakdownItem,
    RankingScore,
)


def candidate_profile_dto_from_scoring(
    candidate: Candidate,
    scores: list[CompetencyScore],
    competencies: list[Competency] | None = None,
    category_names_by_id: Mapping[UUID, str] | None = None,
) -> CandidateProfileDTO:
    competencies_by_id: dict[UUID, Competency] = {
        competency.id: competency for competency in (competencies or [])
    }
    category_names = category_names_by_id or {}
    total_score = (
        sum(s.confidence for s in scores) / len(scores) * 100 if scores else 0.0
    )
    return CandidateProfileDTO(
        candidate_id=candidate.id,
        external_id=candidate.external_id,
        competency_scores=[
            CompetencyScoreDTO(
                competency_id=s.competency_id,
                competency_name=(
                    competencies_by_id[s.competency_id].name
                    if s.competency_id in competencies_by_id
                    else ""
                ),
                competency_description=(
                    competencies_by_id[s.competency_id].description
                    if s.competency_id in competencies_by_id
                    else ""
                ),
                category_id=(
                    competencies_by_id[s.competency_id].category_id
                    if s.competency_id in competencies_by_id
                    else None
                ),
                category_name=(
                    category_names.get(
                        competencies_by_id[s.competency_id].category_id, ""
                    )
                    if s.competency_id in competencies_by_id
                    else ""
                ),
                level=s.level,
                confidence=s.confidence,
            )
            for s in scores
        ],
        total_score=total_score,
    )


def test_result_dto_from_domain(result: TestResult) -> TestResultDTO:
    llm = result.llm_assessment
    return TestResultDTO(
        id=result.id,
        candidate_id=result.candidate_id,
        task_id=result.task_id,
        passed=result.passed,
        score=result.score,
        attempts=result.attempts,
        code_submitted=result.code_submitted,
        question_answers=[
            {"question": item.question, "answer": item.answer}
            for item in result.question_answers
        ],
        llm_assessment={
            "passed": llm.passed,
            "score": llm.score,
            "feedback": llm.feedback,
            "criteria_version": llm.criteria_version,
            "raw_test_score": llm.raw_test_score,
            "penalized_test_score": llm.penalized_test_score,
            "attempt_penalty_applied": llm.attempt_penalty_applied,
            "final_score": llm.final_score,
            "feedback_items": [
                {
                    "type": item.type.value,
                    "value": item.value,
                    "position": item.position,
                }
                for item in llm.feedback_items
            ],
        }
        if llm
        else None,
        created_at=result.created_at,
    )


def ranking_breakdown_item_dto_from_domain(
    breakdown: RankingBreakdownItem,
) -> RankingBreakdownItemDTO:
    return RankingBreakdownItemDTO(
        competency_id=breakdown.competency_id,
        competency_name=breakdown.competency_name,
        required=breakdown.required,
        matched_weight=breakdown.matched_weight,
        total_weight=breakdown.total_weight,
        coverage=breakdown.coverage,
        score_contribution=breakdown.score_contribution,
        matched_subcompetency_ids=list(breakdown.matched_subcompetency_ids),
        total_subcompetency_ids=list(breakdown.total_subcompetency_ids),
    )


def ranking_item_dto_from_ranking_score_domain(
    ranking_score: RankingScore,
) -> RankingItemDTO:
    return RankingItemDTO(
        candidate_id=ranking_score.candidate_id,
        candidate_external_id=ranking_score.candidate_external_id,
        total_score=ranking_score.total_score,
        required_match=ranking_score.required_match,
        desired_match=ranking_score.desired_match,
        required_score=ranking_score.required_score,
        desired_score=ranking_score.desired_score,
        breakdown=[
            ranking_breakdown_item_dto_from_domain(breakdown)
            for breakdown in ranking_score.breakdown
        ],
    )


def task_dto_from_domain(task: Task) -> TaskDTO:
    return TaskDTO(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        description=task.description,
        type=task.type,
        status=task.status,
        category_nodes=[
            TaskCategoryNodeDTO(
                id=node.id,
                task_id=node.task_id,
                category_id=node.category_id,
                position=node.position,
                category_name=node.category.name if node.category else "",
                category_description=node.category.description if node.category else "",
                category_emoji=node.category.emoji if node.category else "",
            )
            for node in task.category_nodes
        ],
        competency_nodes=[
            TaskCompetencyNodeDTO(
                id=node.id,
                task_id=node.task_id,
                competency_id=node.competency_id,
                category_id=node.category_id,
                is_required=node.is_required,
                position=node.position,
                competency_name=node.competency.name if node.competency else "",
                competency_description=(
                    node.competency.description if node.competency else ""
                ),
            )
            for node in task.competency_nodes
        ],
        sub_competency_nodes=[
            TaskSubCompetencyNodeDTO(
                id=node.id,
                task_id=node.task_id,
                sub_competency_id=node.sub_competency_id,
                competency_id=node.competency_id,
                target_level=node.target_level,
                weight=node.weight,
                position=node.position,
                sub_competency_name=(
                    node.sub_competency.name if node.sub_competency else ""
                ),
                sub_competency_description=(
                    node.sub_competency.description if node.sub_competency else ""
                ),
            )
            for node in task.sub_competency_nodes
        ],
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def task_list_item_dto_from_domain(task: Task) -> TaskListItemDTO:
    return TaskListItemDTO(
        id=task.id,
        external_id=task.external_id,
        title=task.title,
        type=task.type,
        status=task.status,
        created_at=task.created_at,
    )


def vacancy_dto_from_domain(vacancy: Vacancy) -> VacancyDTO:
    return VacancyDTO(
        id=vacancy.id,
        name=vacancy.name,
        description=vacancy.description,
        status=vacancy.status,
        category_nodes=[
            VacancyCategoryNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                category_id=node.category_id,
                position=node.position,
                category_name=node.category.name if node.category else "",
                category_description=node.category.description if node.category else "",
                category_emoji=node.category.emoji if node.category else "",
            )
            for node in vacancy.category_nodes
        ],
        competency_nodes=[
            VacancyCompetencyNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                competency_id=node.competency_id,
                category_id=node.category_id,
                is_required=node.is_required,
                position=node.position,
                competency_name=node.competency.name if node.competency else "",
                competency_description=(
                    node.competency.description if node.competency else ""
                ),
            )
            for node in vacancy.competency_nodes
        ],
        sub_competency_nodes=[
            VacancySubCompetencyNodeDTO(
                id=node.id,
                vacancy_id=node.vacancy_id,
                sub_competency_id=node.sub_competency_id,
                competency_id=node.competency_id,
                target_level=node.target_level,
                weight=node.weight,
                position=node.position,
                sub_competency_name=(
                    node.sub_competency.name if node.sub_competency else ""
                ),
                sub_competency_description=(
                    node.sub_competency.description if node.sub_competency else ""
                ),
            )
            for node in vacancy.sub_competency_nodes
        ],
        error_message=vacancy.error_message,
        deleted_at=vacancy.deleted_at,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def suggestion_dto_from_domain(
    suggestion: VacancyGraphSuggestion,
) -> VacancyGraphSuggestionDTO:
    return VacancyGraphSuggestionDTO(
        id=suggestion.id,
        vacancy_id=suggestion.vacancy_id,
        stage=suggestion.stage,
        entity_type=suggestion.entity_type,
        status=suggestion.status,
        name=suggestion.name,
        description=suggestion.description,
        reason=suggestion.reason,
        parent_category_id=suggestion.parent_category_id,
        parent_competency_id=suggestion.parent_competency_id,
        is_required=suggestion.is_required,
        target_level=suggestion.target_level,
        weight=suggestion.weight,
    )


def vacancy_list_item_dto_from_domain(vacancy: Vacancy) -> VacancyListItemDTO:
    return VacancyListItemDTO(
        id=vacancy.id,
        name=vacancy.name,
        status=vacancy.status,
        deleted_at=vacancy.deleted_at,
        created_at=vacancy.created_at,
    )
