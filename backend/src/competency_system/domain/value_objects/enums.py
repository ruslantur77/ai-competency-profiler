from __future__ import annotations

from enum import StrEnum, auto


class VacancyStatus(StrEnum):
    """Status of vacancy processing."""

    DRAFT = auto()
    EXTRACTING = auto()  # LLM pipeline running
    READY = auto()
    FAILED = auto()


class TaskType(StrEnum):
    """Type of testing task."""

    CODE = auto()
    TEST = auto()


class TaskMappingStatus(StrEnum):
    """Status of task to competency mapping pipeline."""

    PENDING = auto()
    COMPLETED = auto()
    FAILED = auto()


class AssessmentStatus(StrEnum):
    """Status of candidate assessment."""

    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()


class SuggestionStage(StrEnum):
    """Pipeline stage that produced suggestion."""

    CATEGORY = auto()
    COMPETENCY = auto()
    SUB_COMPETENCY = auto()


class SuggestionStatus(StrEnum):
    """Expert review status for suggestion."""

    PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()


class SuggestionEntityType(StrEnum):
    """Kind of entity proposed by LLM."""

    CATEGORY = auto()
    COMPETENCY = auto()
    SUB_COMPETENCY = auto()


class WebhookEventStatus(StrEnum):
    """Status of webhook event processing."""

    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()


class UserRole(StrEnum):
    """Authorization role for API access."""

    ADMIN = auto()
    EXPERT = auto()
    HR = auto()
    SYSTEM = auto()
