from typing import Optional

from pydantic import BaseModel


# --- Вакансия ---
class VacancyRequest(BaseModel):
    url: str


class VacancyResponse(BaseModel):
    session_id: str
    vacancy_name: str
    vacancy_text: str
    experience: str
    key_skills: list[str]


# --- Граф ---
class GraphResponse(BaseModel):
    vacancy: dict
    categories: list[dict]
    competencies: list[dict]


# --- Категории ---
class UpdateCategoryRequest(BaseModel):
    category_id: str
    name: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None


class AddCategoryRequest(BaseModel):
    name: str
    emoji: str = "📌"
    description: str = ""


class DeleteCategoryRequest(BaseModel):
    category_id: str


class AiFixCategoryRequest(BaseModel):
    category_id: str
    instruction: str


# --- Компетенции ---
class UpdateCompetencyRequest(BaseModel):
    competency_id: str
    skill: Optional[str] = None
    category_id: Optional[str] = None


class AddCompetencyRequest(BaseModel):
    category_id: str
    skill: str


class DeleteCompetencyRequest(BaseModel):
    competency_id: str


class AiFixCompetencyRequest(BaseModel):
    competency_id: str
    instruction: str


# --- Подкомпетенции ---
class UpdateSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str
    name: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    sub_skills: Optional[list[str]] = None


class AddSubCompetencyRequest(BaseModel):
    competency_id: str
    name: str
    level: str = "intermediate"
    description: str = ""
    sub_skills: list[str] = []


class DeleteSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str


class AiFixSubRequest(BaseModel):
    competency_id: str
    sub_competency_id: Optional[str] = None
    instruction: str
