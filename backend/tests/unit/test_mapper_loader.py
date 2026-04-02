from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, attributes

from competency_system.domain.entities import Candidate, Vacancy
from competency_system.infrastructure.persistence.mappers import _load_all
from competency_system.infrastructure.persistence.models import (
    AssessmentStatus,
    Base,
    CandidateOrm,
    VacancyOrm,
    VacancyStatus,
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def make_candidate(
    session: Session,
    *,
    load_vacancy: bool = False,
    load_achievements: bool = False,
    load_test_results: bool = False,
    load_webhook_events: bool = False,
) -> CandidateOrm:
    """
    Создаёт CandidateOrm в сессии и затем expire-ит те relationship,
    которые мы НЕ хотим загружать — имитируя lazy='raise' без реального запроса.
    """
    candidate = CandidateOrm(
        id=uuid4(),
        external_id="ext-123",
        vacancy_id=uuid4(),
        status=AssessmentStatus.PENDING,
        last_assessment_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Добавляем в сессию чтобы SQLAlchemy знал об объекте
    # (без flush/commit — никакого реального INSERT)
    session.add(candidate)
    session.flush()  # Присваивает identity map, но не коммитит

    # Помечаем незагруженные relationship как expired —
    # sa_inspect(obj).unloaded будет содержать их имена
    relationships = ["vacancy", "achievements", "test_results", "webhook_events"]
    load_flags = {
        "vacancy": load_vacancy,
        "achievements": load_achievements,
        "test_results": load_test_results,
        "webhook_events": load_webhook_events,
    }

    # state = sa_inspect(candidate)

    for rel in relationships:
        if not load_flags[rel]:
            # expire конкретного атрибута → он попадёт в state.unloaded
            state = attributes.instance_state(candidate)
            # Удаляем значение из dict
            state.dict.pop(rel, None)
            # Через приватный метод добавляем в набор незагруженных
            state._expire_attributes(state.dict, [rel])
        else:
            # Для загруженных — проставляем значение вручную
            if rel == "vacancy":
                candidate.vacancy = _make_vacancy(session, candidate.vacancy_id)
            elif rel == "achievements":
                candidate.achievements = []
            elif rel == "test_results":
                candidate.test_results = []
            elif rel == "webhook_events":
                candidate.webhook_events = []

    session.expunge(candidate)  # Убираем из сессии — дальше работаем "офлайн"
    return candidate


def _make_vacancy(session: Session, vacancy_id: UUID):
    vacancy = VacancyOrm(
        name="Backend Engineer",
        description="Build APIs",
        status=VacancyStatus.READY,
    )
    session.add(vacancy)
    session.flush()
    session.expunge(vacancy)
    return vacancy


class TestLoadAll:
    def test_loads_scalar_fields_only(self, session):
        """Только скалярные поля загружены, все relationship — unloaded."""
        candidate = make_candidate(session)

        result = _load_all(candidate, Candidate)

        assert isinstance(result, Candidate)
        assert result.external_id == "ext-123"
        assert result.status == AssessmentStatus.PENDING
        assert result.last_assessment_at is None
        # Relationship не попали в результат (они в unloaded)
        assert result.vacancy is None
        assert result.achievements == []

    def test_loads_with_vacancy(self, session):
        """Vacancy загружена вручную — должна попасть в домен как dict."""
        candidate = make_candidate(session, load_vacancy=True)

        result = _load_all(candidate, Candidate)

        assert result.vacancy is not None
        assert isinstance(result.vacancy, Vacancy)  # serialize() вернул dict

    def test_loads_with_empty_achievements(self, session):
        """Achievements загружены как пустой список."""
        candidate = make_candidate(session, load_achievements=True)

        result = _load_all(candidate, Candidate)

        assert result.achievements == []

    def test_raises_for_non_orm(self, session):
        """Передача не-ORM объекта должна бросать ValueError."""
        with pytest.raises(ValueError, match="only orm models"):
            _load_all(MagicMock(spec=[]), Candidate)

    def test_raises_for_non_dataclass_domain(self, session):
        """domain_model должен быть dataclass."""
        candidate = make_candidate(session)

        class NotADataclass:
            def __init__(self, **kwargs):
                pass

        with pytest.raises(TypeError, match="domain_model must be a dataclass"):
            _load_all(candidate, NotADataclass)

    def test_all_relationships_loaded(self, session):
        """Все relationship загружены — все попадают в домен."""
        candidate = make_candidate(
            session,
            load_vacancy=True,
            load_achievements=True,
            load_test_results=True,
            load_webhook_events=True,
        )

        result = _load_all(candidate, Candidate)

        assert result.vacancy is not None
        assert isinstance(result.achievements, list)
        assert isinstance(result.test_results, list)
