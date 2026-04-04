from __future__ import annotations

from uuid import UUID, uuid4

from competency_system.application.dtos.webhooks import (
    WebhookEvent,
    WebhookEventPayload,
)
from competency_system.domain.entities import (
    Candidate,
    Category,
    Competency,
    SubCompetency,
    Vacancy,
)
from competency_system.domain.entities import (
    TestResult as DomainTestResult,
)
from competency_system.domain.entities import (
    TestResultLLMAssessment as DomainTestResultLLMAssessment,
)
from competency_system.domain.entities import (
    TestResultLLMFeedbackItem as DomainTestResultLLMFeedbackItem,
)
from competency_system.domain.value_objects import LLMFeedbackType
from competency_system.infrastructure.persistence.mappers import (
    candidate_to_orm,
    category_to_orm,
    competency_to_orm,
    vacancy_to_orm,
    webhook_event_to_orm,
)
from competency_system.infrastructure.persistence.mappers import (
    test_result_to_orm as map_test_result_to_orm,
)
from competency_system.infrastructure.persistence.models import (
    POLICY_STRICT,
    UNSET,
)


def test_domain_to_orm_dumps_loaded_relationships() -> None:
    sub = SubCompetency(name="REST", description="API", weight=0.7)
    competency = Competency(
        category_id=UUID(int=0),
        name="Backend",
        description="Core",
        sub_competencies=[sub],
    )
    category = Category(name="Engineering", competencies=[competency])
    competency.category_id = category.id
    sub.competency_id = competency.id

    orm = category_to_orm(category)

    assert len(orm.competencies) == 1
    assert orm.competencies[0].name == "Backend"
    assert len(orm.competencies[0].sub_competencies) == 1
    assert orm.competencies[0].sub_competencies[0].name == "REST"


def test_domain_to_orm_handles_cyclic_relationships() -> None:
    sub = SubCompetency(name="REST")
    competency = Competency(
        category_id=UUID(int=0),
        name="Backend",
        sub_competencies=[sub],
    )
    category = Category(name="Engineering", competencies=[competency])
    competency.category_id = category.id
    competency.category = category
    sub.competency_id = competency.id
    sub.competency = competency

    orm = category_to_orm(category)

    assert orm.competencies[0].category is orm
    assert orm.competencies[0].sub_competencies[0].competency is orm.competencies[0]


def test_present_fields_distinguishes_omitted_from_explicit_none() -> None:
    vacancy = Vacancy(name="Backend", description="Build APIs", error_message=None)

    omitted = vacancy_to_orm(vacancy, present_fields={"name", "description"})
    explicit_null = vacancy_to_orm(vacancy, present_fields={"error_message"})

    assert "error_message" not in omitted.__dict__
    assert "error_message" in explicit_null.__dict__
    assert explicit_null.error_message is None


def test_unset_value_is_not_dumped_even_if_marked_present() -> None:
    candidate = Candidate(external_id="cand-1", vacancy_id=uuid4())
    candidate.last_assessment_at = UNSET

    orm = candidate_to_orm(candidate, present_fields={"last_assessment_at"})

    assert "last_assessment_at" not in orm.__dict__


def test_nested_present_fields_for_relationship_dump() -> None:
    result = DomainTestResult(candidate_id=uuid4(), task_id=uuid4())
    assessment = DomainTestResultLLMAssessment(
        test_result_id=result.id,
        feedback_items=[
            DomainTestResultLLMFeedbackItem(
                assessment_id=uuid4(),
                type=LLMFeedbackType.POSITIVE,
                value="Strong structure",
                position=0,
            )
        ],
    )
    result.llm_assessment = assessment

    orm = map_test_result_to_orm(
        result,
        present_fields={"llm_assessment.feedback_items"},
    )

    assert orm.llm_assessment is not None
    assert "score" not in orm.llm_assessment.__dict__
    assert len(orm.llm_assessment.feedback_items) == 1


def test_default_policy_ignores_none_relationships() -> None:
    competency = Competency(category_id=uuid4(), name="Backend")

    orm = competency_to_orm(competency)

    assert "category" not in orm.__dict__


def test_default_policy_ignores_empty_relationship_collections() -> None:
    category = Category(name="Engineering", competencies=[])

    orm = category_to_orm(category)

    assert "competencies" not in orm.__dict__


def test_strict_policy_applies_relationship_none_and_empty_collection() -> None:
    category = Category(name="Engineering", competencies=[])

    orm = category_to_orm(category, policy=POLICY_STRICT)

    assert "competencies" in orm.__dict__
    assert orm.competencies == []


def test_webhook_payload_dumped_as_dict() -> None:
    event = WebhookEvent(
        event_id="evt-1",
        vacancy_id=uuid4(),
        candidate_external_id="candidate",
        task_external_id="task",
        payload=WebhookEventPayload(data={"a": 1}),
    )

    orm = webhook_event_to_orm(event)

    assert orm.payload == {"a": 1}
