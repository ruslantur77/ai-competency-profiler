from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VacancyStatus(StrEnum):
    EXTRACTING = "extracting"
    READY = "ready"


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

    class Config:
        from_attributes = True


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


class VacancyResponse(BaseModel):
    session_id: str
    vacancy_name: str
    vacancy_text: str
    experience: str
    key_skills: list[str]


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
    ai_suggestion: dict[str, str]


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
    sub_competency_id: str | None = None
    instruction: str


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    status: str
    message: str


class CreateResponse[T: BaseModel](BaseModel):
    status: str
    message: str
    created: T


class UpdateResponse[T: BaseModel](BaseModel):
    status: str
    message: str
    updated: T
