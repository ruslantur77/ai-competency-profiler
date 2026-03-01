from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from llm_service import build_graph
from schemas import (
    AddCategoryRequest,
    AddCompetencyRequest,
    AddSubCompetencyRequest,
    AiFixCategoryRequest,
    AiFixCategoryResponse,
    AiFixCompetencyRequest,
    AiFixSubRequest,
    CategoryNode,
    CompetencyNode,
    CreateVacancyRequest,
    DeleteCategoryRequest,
    DeleteCompetencyRequest,
    DeleteSubCompetencyRequest,
    GraphResponse,
    ImportHHRequest,
    ImportHHResponse,
    StatusResponse,
    SubCompetency,
    UpdateCategoryRequest,
    UpdateCompetencyRequest,
    UpdateSubCompetencyRequest,
    UpdateVacancyRequest,
    Vacancy,
    VacancyList,
    VacancyListItem,
    VacancyNode,
    VacancyStatus,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Competency Profiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
vacancies_db: dict[str, Vacancy] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_vacancy(vacancy_id: str) -> Vacancy:
    vacancy = vacancies_db.get(vacancy_id)
    if vacancy is None:
        raise HTTPException(404, "Вакансия не найдена")
    return vacancy


def _get_graph(vacancy_id: str) -> GraphResponse:
    vacancy = _get_vacancy(vacancy_id)
    if vacancy.graph is None:
        raise HTTPException(409, "Граф ещё не построен")
    return vacancy.graph


def _find_category(graph: GraphResponse, category_id: str) -> CategoryNode:
    for cat in graph.categories:
        if cat.id == category_id:
            return cat
    raise HTTPException(404, "Категория не найдена")


def _find_competency(graph: GraphResponse, competency_id: str) -> CompetencyNode:
    for comp in graph.competencies:
        if comp.id == competency_id:
            return comp
    raise HTTPException(404, "Компетенция не найдена")


def _find_sub_competency(comp: CompetencyNode, sub_id: str) -> SubCompetency:
    for sub in comp.sub_competencies:
        if sub.id == sub_id:
            return sub
    raise HTTPException(404, "Подкомпетенция не найдена")


# ---------------------------------------------------------------------------
# Vacancies
# ---------------------------------------------------------------------------


@app.get("/api/vacancies", response_model=VacancyList)
async def list_vacancies() -> VacancyList:
    items = [
        VacancyListItem.model_validate(v, from_attributes=True)
        for v in vacancies_db.values()
    ]
    return VacancyList(vacancies=items)


@app.post("/api/vacancies")
async def create_vacancy(req: CreateVacancyRequest) -> dict:
    vacancy_id = uuid.uuid4().hex[:8]
    vacancy = Vacancy(
        id=vacancy_id,
        name=req.name,
        description=req.description,
        status=VacancyStatus.EXTRACTING,
        created_at=datetime.now(UTC),
        graph=None,
        hh_key_skills=[],
        experience="",
    )
    vacancies_db[vacancy_id] = vacancy

    # TODO: вынести в background task (BackgroundTasks / celery)
    try:
        graph = build_graph({"name": req.name, "text": req.description})
        vacancy.graph = graph
    except Exception:
        pass

    vacancy.status = VacancyStatus.READY

    return {
        "status": "ok",
        "vacancy": VacancyListItem.model_validate(vacancy, from_attributes=True),
    }


@app.post("/api/vacancies/import-hh", response_model=ImportHHResponse)
async def import_from_hh(req: ImportHHRequest) -> ImportHHResponse:
    match = re.search(r"vacancy/(\d+)", req.url) or re.search(r"(\d{6,})", req.url)
    if not match:
        raise HTTPException(400, "Не удалось извлечь ID вакансии из ссылки")

    hh_vacancy_id = match.group(1)
    hh_url = f"https://api.hh.ru/vacancies/{hh_vacancy_id}"

    try:
        resp = requests.get(
            hh_url, headers={"User-Agent": "CompetencyProfiler/1.0"}, timeout=10
        )
    except requests.RequestException as exc:
        raise HTTPException(400, f"Ошибка сети: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(400, f"hh.ru вернул ошибку: {resp.status_code}")

    data = resp.json()
    clean_text = (
        BeautifulSoup(data.get("description", ""), "html.parser")
        .get_text(separator="\n")
        .strip()
    )

    return ImportHHResponse(
        status="ok",
        name=data.get("name", ""),
        description=clean_text,
        experience=data.get("experience", {}).get("name", ""),
        key_skills=[s["name"] for s in data.get("key_skills", [])],
    )


@app.get("/api/vacancies/{vacancy_id}")
async def get_vacancy(vacancy_id: str) -> dict:
    v = _get_vacancy(vacancy_id)
    return {
        "id": v.id,
        "name": v.name,
        "description": v.description,
        "status": v.status,
        "created_at": v.created_at,
        "experience": v.experience,
        "key_skills": v.hh_key_skills,
    }


@app.put("/api/vacancies/{vacancy_id}", response_model=StatusResponse)
async def update_vacancy(vacancy_id: str, req: UpdateVacancyRequest) -> StatusResponse:
    v = _get_vacancy(vacancy_id)
    if req.name is not None:
        v.name = req.name
        if v.graph is not None:
            v.graph.vacancy = VacancyNode(name=req.name)
    if req.description is not None:
        v.description = req.description
    return StatusResponse(status="ok", message="Вакансия обновлена")


@app.delete("/api/vacancies/{vacancy_id}", response_model=StatusResponse)
async def delete_vacancy(vacancy_id: str) -> StatusResponse:
    _get_vacancy(vacancy_id)
    del vacancies_db[vacancy_id]
    return StatusResponse(status="ok", message="Вакансия удалена")


@app.get("/api/vacancies/{vacancy_id}/status")
async def get_vacancy_status(vacancy_id: str) -> dict:
    v = _get_vacancy(vacancy_id)
    return {"status": v.status}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@app.get("/api/vacancies/{vacancy_id}/graph", response_model=GraphResponse)
async def get_graph(vacancy_id: str) -> GraphResponse:
    return _get_graph(vacancy_id)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/category")
async def update_category(vacancy_id: str, req: UpdateCategoryRequest) -> dict:
    graph = _get_graph(vacancy_id)
    cat = _find_category(graph, req.category_id)

    if req.name is not None:
        cat.name = req.name
    if req.emoji is not None:
        cat.emoji = req.emoji
    if req.description is not None:
        cat.description = req.description

    return {
        "status": "ok",
        "message": f"Категория '{cat.name}' обновлена",
        "updated": cat,
    }


@app.post("/api/vacancies/{vacancy_id}/category")
async def add_category(vacancy_id: str, req: AddCategoryRequest) -> dict:
    graph = _get_graph(vacancy_id)
    new_cat = CategoryNode(
        id=f"cat_{uuid.uuid4().hex[:6]}",
        name=req.name,
        emoji=req.emoji,
        description=req.description,
    )
    graph.categories.append(new_cat)
    return {
        "status": "ok",
        "message": f"Категория '{req.name}' добавлена",
        "created": new_cat,
    }


@app.delete("/api/vacancies/{vacancy_id}/category", response_model=StatusResponse)
async def delete_category(
    vacancy_id: str, req: DeleteCategoryRequest
) -> StatusResponse:
    graph = _get_graph(vacancy_id)
    original_len = len(graph.categories)
    graph.categories = [c for c in graph.categories if c.id != req.category_id]

    if len(graph.categories) == original_len:
        raise HTTPException(404, "Категория не найдена")

    graph.competencies = [
        c for c in graph.competencies if c.category_id != req.category_id
    ]
    return StatusResponse(status="ok", message="Категория удалена")


@app.post(
    "/api/graph/{session_id}/ai-fix-category", response_model=AiFixCategoryResponse
)
async def ai_fix_category(
    session_id: str, req: AiFixCategoryRequest
) -> AiFixCategoryResponse:
    _get_vacancy(session_id)
    return AiFixCategoryResponse(
        status="ok",
        message=f"🤖 AI получил инструкцию: '{req.instruction}'. Категория будет обновлена. (Mock)",
        ai_suggestion={
            "name": "[AI] Обновлённая категория",
            "emoji": "🔮",
            "description": f"Сгенерировано AI: {req.instruction}",
        },
    )


# ---------------------------------------------------------------------------
# Competencies
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/competency")
async def update_competency(vacancy_id: str, req: UpdateCompetencyRequest) -> dict:
    graph = _get_graph(vacancy_id)
    comp = _find_competency(graph, req.competency_id)

    if req.skill is not None:
        comp.skill = req.skill
    if req.category_id is not None:
        # Убеждаемся, что целевая категория существует
        _find_category(graph, req.category_id)
        comp.category_id = req.category_id

    return {"status": "ok", "message": "Компетенция обновлена", "updated": comp}


@app.post("/api/vacancies/{vacancy_id}/competency")
async def add_competency(vacancy_id: str, req: AddCompetencyRequest) -> dict:
    graph = _get_graph(vacancy_id)
    _find_category(graph, req.category_id)  # проверяем существование

    new_comp = CompetencyNode(
        id=f"comp_{uuid.uuid4().hex[:6]}",
        category_id=req.category_id,
        skill=req.skill,
        sub_competencies=[],
    )
    graph.competencies.append(new_comp)
    return {"status": "ok", "message": f"'{req.skill}' добавлена", "created": new_comp}


@app.delete("/api/vacancies/{vacancy_id}/competency", response_model=StatusResponse)
async def delete_competency(
    vacancy_id: str, req: DeleteCompetencyRequest
) -> StatusResponse:
    graph = _get_graph(vacancy_id)
    original_len = len(graph.competencies)
    graph.competencies = [c for c in graph.competencies if c.id != req.competency_id]

    if len(graph.competencies) == original_len:
        raise HTTPException(404, "Компетенция не найдена")

    return StatusResponse(status="ok", message="Компетенция удалена")


@app.post(
    "/api/vacancies/{vacancy_id}/ai-fix-competency", response_model=StatusResponse
)
async def ai_fix_competency(
    vacancy_id: str, req: AiFixCompetencyRequest
) -> StatusResponse:
    _get_vacancy(vacancy_id)
    return StatusResponse(
        status="ok",
        message=f"🤖 AI получил инструкцию: '{req.instruction}'. (Mock)",
    )


# ---------------------------------------------------------------------------
# Sub-competencies
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/sub-competency")
async def update_sub_competency(
    vacancy_id: str, req: UpdateSubCompetencyRequest
) -> dict:
    graph = _get_graph(vacancy_id)
    comp = _find_competency(graph, req.competency_id)
    sub = _find_sub_competency(comp, req.sub_competency_id)

    if req.name is not None:
        sub.name = req.name
    if req.level is not None:
        sub.level = req.level
    if req.description is not None:
        sub.description = req.description
    if req.sub_skills is not None:
        sub.sub_skills = req.sub_skills

    return {"status": "ok", "message": f"'{sub.name}' обновлена", "updated": sub}


@app.post("/api/vacancies/{vacancy_id}/sub-competency")
async def add_sub_competency(vacancy_id: str, req: AddSubCompetencyRequest) -> dict:
    graph = _get_graph(vacancy_id)
    comp = _find_competency(graph, req.competency_id)

    new_sub = SubCompetency(
        id=f"sub_{uuid.uuid4().hex[:6]}",
        name=req.name,
        level=req.level,
        description=req.description,
        sub_skills=req.sub_skills,
    )
    comp.sub_competencies.append(new_sub)
    return {"status": "ok", "message": f"'{req.name}' добавлена", "created": new_sub}


@app.delete("/api/vacancies/{vacancy_id}/sub-competency", response_model=StatusResponse)
async def delete_sub_competency(
    vacancy_id: str, req: DeleteSubCompetencyRequest
) -> StatusResponse:
    graph = _get_graph(vacancy_id)
    comp = _find_competency(graph, req.competency_id)

    original_len = len(comp.sub_competencies)
    comp.sub_competencies = [
        s for s in comp.sub_competencies if s.id != req.sub_competency_id
    ]

    if len(comp.sub_competencies) == original_len:
        raise HTTPException(404, "Подкомпетенция не найдена")

    return StatusResponse(status="ok", message="Подкомпетенция удалена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix", response_model=StatusResponse)
async def ai_fix_sub(vacancy_id: str, req: AiFixSubRequest) -> StatusResponse:
    _get_vacancy(vacancy_id)
    return StatusResponse(
        status="ok",
        message=f"🤖 AI получил инструкцию: '{req.instruction}'. (Mock)",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
