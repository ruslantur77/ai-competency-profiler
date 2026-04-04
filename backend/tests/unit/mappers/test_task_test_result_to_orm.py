from __future__ import annotations

import pytest

from competency_system.domain.value_objects.enums import LLMFeedbackType
from competency_system.infrastructure.persistence.mappers import (
    task_to_orm,
    test_result_to_orm as map_test_result_to_orm,
)
from competency_system.infrastructure.persistence.models import UNSET
from tests.factories import (
    SubCompetencyFactory,
    TaskFactory,
    TaskSubCompetencyMappingFactory,
    TestResultFactory,
    TestResultLLMAssessmentFactory,
    TestResultLLMFeedbackItemFactory,
    TestResultQuestionAnswerFactory,
)

from .conftest import PolicyCase, assert_field_omitted, assert_field_set


def test_task_to_orm_default_is_scalar_only(policy_case: PolicyCase) -> None:
    mapping = TaskSubCompetencyMappingFactory().make()
    task = TaskFactory().make({"sub_competency_mappings": [mapping]})

    orm = task_to_orm(task, policy=policy_case.policy)

    assert_field_set(orm, "external_id")
    assert_field_omitted(orm, "sub_competency_mappings")


@pytest.mark.parametrize("as_empty", [False, True], ids=["none", "empty"])
def test_task_to_orm_collection_relationship_policy(
    policy_case: PolicyCase,
    as_empty: bool,
) -> None:
    task = TaskFactory().make({"sub_competency_mappings": []})
    if not as_empty:
        task.sub_competency_mappings = None  # type: ignore[assignment]

    if not as_empty and policy_case.applies_relationship_none:
        with pytest.raises(TypeError):
            task_to_orm(
                task,
                present_fields={"sub_competency_mappings"},
                policy=policy_case.policy,
            )
        return

    orm = task_to_orm(
        task,
        present_fields={"sub_competency_mappings"},
        policy=policy_case.policy,
    )

    if as_empty:
        if policy_case.applies_empty_relationship:
            assert_field_set(orm, "sub_competency_mappings")
            assert orm.sub_competency_mappings == []
        else:
            assert_field_omitted(orm, "sub_competency_mappings")
    else:
        assert_field_omitted(orm, "sub_competency_mappings")


def test_task_to_orm_nested_mappings_dump(policy_case: PolicyCase) -> None:
    sub = SubCompetencyFactory().make()
    mapping = TaskSubCompetencyMappingFactory().make(
        {"sub_competency_id": sub.id, "sub_competency": sub}
    )
    task = TaskFactory().make({"sub_competency_mappings": [mapping]})

    orm = task_to_orm(
        task,
        present_fields={"sub_competency_mappings", "sub_competency_mappings.sub_competency"},
        policy=policy_case.policy,
    )
    assert len(orm.sub_competency_mappings) == 1
    assert orm.sub_competency_mappings[0].sub_competency_id == sub.id


def test_test_result_to_orm_default_is_scalar_only(policy_case: PolicyCase) -> None:
    result = TestResultFactory().make(
        {
            "question_answers": [TestResultQuestionAnswerFactory().make()],
            "llm_assessment": TestResultLLMAssessmentFactory().make(),
        }
    )

    orm = map_test_result_to_orm(result, policy=policy_case.policy)

    assert_field_set(orm, "score")
    assert_field_omitted(orm, "question_answers")
    assert_field_omitted(orm, "llm_assessment")


def test_test_result_scalar_none_code_submitted_by_policy(policy_case: PolicyCase) -> None:
    result = TestResultFactory().make({"code_submitted": None})

    orm = map_test_result_to_orm(result, policy=policy_case.policy)

    if policy_case.applies_scalar_none:
        assert_field_set(orm, "code_submitted")
        assert orm.code_submitted is None
    else:
        assert_field_omitted(orm, "code_submitted")


def test_test_result_nested_assessment_feedback_items(policy_case: PolicyCase) -> None:
    feedback_item = TestResultLLMFeedbackItemFactory().make(
        {"type": LLMFeedbackType.POSITIVE, "value": "Strong"}
    )
    assessment = TestResultLLMAssessmentFactory().make({"feedback_items": [feedback_item]})
    result = TestResultFactory().make({"llm_assessment": assessment})

    orm = map_test_result_to_orm(
        result,
        present_fields={"llm_assessment.feedback_items"},
        policy=policy_case.policy,
    )

    assert orm.llm_assessment is not None
    assert "score" not in orm.llm_assessment.__dict__
    assert len(orm.llm_assessment.feedback_items) == 1


def test_test_result_relationship_none_policy(policy_case: PolicyCase) -> None:
    result = TestResultFactory().make({"llm_assessment": None})

    orm = map_test_result_to_orm(
        result,
        present_fields={"llm_assessment"},
        policy=policy_case.policy,
    )

    if policy_case.applies_relationship_none:
        assert_field_set(orm, "llm_assessment")
        assert orm.llm_assessment is None
    else:
        assert_field_omitted(orm, "llm_assessment")


def test_test_result_unset_not_dumped_even_if_present(policy_case: PolicyCase) -> None:
    result = TestResultFactory().make({"code_submitted": None})
    result.code_submitted = UNSET  # type: ignore[assignment]

    orm = map_test_result_to_orm(
        result,
        present_fields={"code_submitted"},
        policy=policy_case.policy,
    )
    assert_field_omitted(orm, "code_submitted")


def test_test_result_question_answers_collection_policy(policy_case: PolicyCase) -> None:
    result = TestResultFactory().make({"question_answers": []})
    result.question_answers = [] if policy_case.applies_empty_relationship else []
    orm = map_test_result_to_orm(
        result,
        present_fields={"question_answers"},
        policy=policy_case.policy,
    )
    if policy_case.applies_empty_relationship:
        assert_field_set(orm, "question_answers")
        assert orm.question_answers == []
    else:
        assert_field_omitted(orm, "question_answers")


def test_task_mapping_allows_explicit_none_relationship(policy_case: PolicyCase) -> None:
    mapping = TaskSubCompetencyMappingFactory().make({"sub_competency": None})
    task = TaskFactory().make({"sub_competency_mappings": [mapping]})

    orm = task_to_orm(
        task,
        present_fields={"sub_competency_mappings", "sub_competency_mappings.sub_competency"},
        policy=policy_case.policy,
    )

    assert len(orm.sub_competency_mappings) == 1
    if policy_case.applies_relationship_none:
        assert_field_set(orm.sub_competency_mappings[0], "sub_competency")
    else:
        assert_field_omitted(orm.sub_competency_mappings[0], "sub_competency")
