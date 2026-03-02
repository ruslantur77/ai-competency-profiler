from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VacancyStatus(StrEnum):
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class CompetencyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------


class CategoryNode(BaseModel):
    id: str
    name: str
    description: str
    emoji: str


class SubCompetency(BaseModel):
    id: str
    name: str
    level: CompetencyLevel
    description: str
    sub_skills: list[str]


class CompetencyNode(BaseModel):
    id: str
    category_id: str
    skill: str
    sub_competencies: list[SubCompetency]


class VacancyNode(BaseModel):
    name: str


class GraphResponse(BaseModel):
    vacancy: VacancyNode
    categories: list[CategoryNode]
    competencies: list[CompetencyNode]


# ---------------------------------------------------------------------------
# Vacancy
# ---------------------------------------------------------------------------


class CreateVacancyRequest(BaseModel):
    name: str
    description: str
    experience: str = ""
    hh_key_skills: list[str] = Field(default_factory=list)


class UpdateVacancyRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class ImportHHRequest(BaseModel):
    url: str


class VacancyRequest(BaseModel):
    url: str


class VacancyListItem(BaseModel):
    id: str
    name: str
    status: VacancyStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class VacancyList(BaseModel):
    vacancies: list[VacancyListItem]


class Vacancy(BaseModel):
    id: str
    name: str
    description: str
    status: VacancyStatus
    created_at: datetime
    graph: GraphResponse | None = None
    hh_key_skills: list[str] = Field(default_factory=list)
    experience: str = ""
    error: str | None = None  # причина ошибки если status=FAILED


class VacancyDetail(BaseModel):
    """Полные данные вакансии для GET /api/vacancies/{id}."""

    id: str
    name: str
    description: str
    status: VacancyStatus
    created_at: datetime
    experience: str
    key_skills: list[str]
    error: str | None


class ImportHHResponse(BaseModel):
    status: str
    name: str
    description: str
    experience: str
    key_skills: list[str]


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class UpdateCategoryRequest(BaseModel):
    category_id: str
    name: str | None = None
    emoji: str | None = None
    description: str | None = None


class AddCategoryRequest(BaseModel):
    name: str
    emoji: str = "📌"
    description: str = ""


class DeleteCategoryRequest(BaseModel):
    category_id: str


class AiFixCategoryRequest(BaseModel):
    category_id: str
    instruction: str


class AiFixCategoryResponse(BaseModel):
    status: str
    message: str
    updated: CategoryNode


# ---------------------------------------------------------------------------
# Competencies
# ---------------------------------------------------------------------------


class UpdateCompetencyRequest(BaseModel):
    competency_id: str
    skill: str | None = None
    category_id: str | None = None


class AddCompetencyRequest(BaseModel):
    category_id: str
    skill: str


class DeleteCompetencyRequest(BaseModel):
    competency_id: str


class AiFixCompetencyRequest(BaseModel):
    competency_id: str
    instruction: str


class AiFixCompetencyResponse(BaseModel):
    status: str
    message: str
    updated: CompetencyNode


# ---------------------------------------------------------------------------
# Sub-competencies
# ---------------------------------------------------------------------------


class UpdateSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str
    name: str | None = None
    level: CompetencyLevel | None = None
    description: str | None = None
    sub_skills: list[str] | None = None


class AddSubCompetencyRequest(BaseModel):
    competency_id: str
    name: str
    level: CompetencyLevel = CompetencyLevel.INTERMEDIATE
    description: str = ""
    sub_skills: list[str] = Field(default_factory=list)


class DeleteSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str


class AiFixSubRequest(BaseModel):
    competency_id: str
    sub_competency_id: str
    instruction: str


class AiFixSubResponse(BaseModel):
    status: str
    message: str
    updated: SubCompetency


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    status: str
    message: str
