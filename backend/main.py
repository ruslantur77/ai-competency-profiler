from __future__ import annotations

import logging
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from llm_service import (
    LLMError,
    VacancyInput,
    ai_fix_category,
    ai_fix_competency,
    ai_fix_sub_competency,
    build_graph,
)
from schemas import (
    AddCategoryRequest,
    AddCompetencyRequest,
    AddSubCompetencyRequest,
    AiFixCategoryRequest,
    AiFixCategoryResponse,
    AiFixCompetencyRequest,
    AiFixCompetencyResponse,
    AiFixSubRequest,
    AiFixSubResponse,
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
    VacancyDetail,
    VacancyList,
    VacancyListItem,
    VacancyNode,
    VacancyStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

_http_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=15.0)
    yield
    await _http_client.aclose()


app = FastAPI(title="Competency Profiler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

vacancies_db: dict[str, Vacancy] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_vacancy(vacancy_id: str) -> Vacancy:
    vacancy = vacancies_db.get(vacancy_id)
    if vacancy is None:
        raise HTTPException(404, "Вакансия не найдена")
    return vacancy


def _get_graph(vacancy: Vacancy) -> GraphResponse:
    if vacancy.graph is None:
        if vacancy.status == VacancyStatus.EXTRACTING:
            raise HTTPException(409, "Граф ещё строится, попробуйте позже")
        raise HTTPException(409, "Граф недоступен")
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


def _find_sub(comp: CompetencyNode, sub_id: str) -> SubCompetency:
    for sub in comp.sub_competencies:
        if sub.id == sub_id:
            return sub
    raise HTTPException(404, "Подкомпетенция не найдена")


# ---------------------------------------------------------------------------
# Background task: build graph
# ---------------------------------------------------------------------------


async def _build_graph_task(vacancy_id: str, name: str, description: str) -> None:
    vacancy = vacancies_db.get(vacancy_id)
    if vacancy is None:
        return

    try:
        graph = await build_graph(VacancyInput(name=name, text=description))
        vacancy.graph = graph
        vacancy.status = VacancyStatus.READY
        logger.info("Граф для вакансии '%s' успешно построен", vacancy_id)
    except Exception as exc:
        vacancy.status = VacancyStatus.FAILED
        vacancy.error = str(exc)
        logger.exception("Ошибка построения графа для вакансии '%s'", vacancy_id)


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


@app.post("/api/vacancies", status_code=202)
async def create_vacancy(
    req: CreateVacancyRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    vacancy_id = uuid.uuid4().hex[:8]
    vacancy = Vacancy(
        id=vacancy_id,
        name=req.name,
        description=req.description,
        status=VacancyStatus.EXTRACTING,
        created_at=datetime.now(UTC),
        hh_key_skills=req.hh_key_skills,
        experience=req.experience,
    )
    vacancies_db[vacancy_id] = vacancy

    background_tasks.add_task(_build_graph_task, vacancy_id, req.name, req.description)

    return {
        "status": "accepted",
        "vacancy": VacancyListItem.model_validate(vacancy, from_attributes=True),
    }


@app.post("/api/vacancies/import-hh", response_model=ImportHHResponse)
async def import_from_hh(req: ImportHHRequest) -> ImportHHResponse:
    match = re.search(r"vacancy/(\d+)", req.url) or re.search(r"(\d{6,})", req.url)
    if not match:
        raise HTTPException(400, "Не удалось извлечь ID вакансии из ссылки")

    hh_id = match.group(1)
    url = f"https://api.hh.ru/vacancies/{hh_id}"

    try:
        resp = await _http_client.get(
            url, headers={"User-Agent": "CompetencyProfiler/1.0"}
        )
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Ошибка сети при обращении к hh.ru: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(502, f"hh.ru вернул ошибку {resp.status_code}")

    data = resp.json()
    description = (
        BeautifulSoup(data.get("description", ""), "html.parser")
        .get_text(separator="\n")
        .strip()
    )

    return ImportHHResponse(
        status="ok",
        name=data.get("name", ""),
        description=description,
        experience=data.get("experience", {}).get("name", ""),
        key_skills=[s["name"] for s in data.get("key_skills", [])],
    )


@app.get("/api/vacancies/{vacancy_id}", response_model=VacancyDetail)
async def get_vacancy(vacancy_id: str) -> VacancyDetail:
    v = _get_vacancy(vacancy_id)
    return VacancyDetail(
        id=v.id,
        name=v.name,
        description=v.description,
        status=v.status,
        created_at=v.created_at,
        experience=v.experience,
        key_skills=v.hh_key_skills,
        error=v.error,
    )


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
    return {"status": v.status, "error": v.error}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@app.get("/api/vacancies/{vacancy_id}/graph", response_model=GraphResponse)
async def get_graph(vacancy_id: str) -> GraphResponse:
    v = _get_vacancy(vacancy_id)
    return _get_graph(v)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/category")
async def update_category(vacancy_id: str, req: UpdateCategoryRequest) -> dict:
    graph = _get_graph(_get_vacancy(vacancy_id))
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
    graph = _get_graph(_get_vacancy(vacancy_id))

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
    graph = _get_graph(_get_vacancy(vacancy_id))

    before = len(graph.categories)
    graph.categories = [c for c in graph.categories if c.id != req.category_id]

    if len(graph.categories) == before:
        raise HTTPException(404, "Категория не найдена")

    # Каскадно удаляем компетенции этой категории
    graph.competencies = [
        c for c in graph.competencies if c.category_id != req.category_id
    ]

    return StatusResponse(status="ok", message="Категория удалена")


@app.post(
    "/api/vacancies/{vacancy_id}/ai-fix-category", response_model=AiFixCategoryResponse
)
async def ai_fix_category_endpoint(
    vacancy_id: str, req: AiFixCategoryRequest
) -> AiFixCategoryResponse:
    v = _get_vacancy(vacancy_id)
    graph = _get_graph(v)
    cat = _find_category(graph, req.category_id)

    try:
        updated = await ai_fix_category(req.instruction, cat, v.description)
    except LLMError as exc:
        raise HTTPException(502, f"Ошибка AI: {exc}") from exc

    # Мутируем in-place, чтобы сохранить объект в списке
    cat.name = updated.name
    cat.emoji = updated.emoji
    cat.description = updated.description

    return AiFixCategoryResponse(
        status="ok", message="Категория обновлена AI", updated=cat
    )


# ---------------------------------------------------------------------------
# Competencies
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/competency")
async def update_competency(vacancy_id: str, req: UpdateCompetencyRequest) -> dict:
    graph = _get_graph(_get_vacancy(vacancy_id))
    comp = _find_competency(graph, req.competency_id)

    if req.skill is not None:
        comp.skill = req.skill
    if req.category_id is not None:
        _find_category(graph, req.category_id)  # проверяем существование
        comp.category_id = req.category_id

    return {"status": "ok", "message": "Компетенция обновлена", "updated": comp}


@app.post("/api/vacancies/{vacancy_id}/competency")
async def add_competency(vacancy_id: str, req: AddCompetencyRequest) -> dict:
    graph = _get_graph(_get_vacancy(vacancy_id))
    _find_category(graph, req.category_id)

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
    graph = _get_graph(_get_vacancy(vacancy_id))

    before = len(graph.competencies)
    graph.competencies = [c for c in graph.competencies if c.id != req.competency_id]

    if len(graph.competencies) == before:
        raise HTTPException(404, "Компетенция не найдена")

    return StatusResponse(status="ok", message="Компетенция удалена")


@app.post(
    "/api/vacancies/{vacancy_id}/ai-fix-competency",
    response_model=AiFixCompetencyResponse,
)
async def ai_fix_competency_endpoint(
    vacancy_id: str, req: AiFixCompetencyRequest
) -> AiFixCompetencyResponse:
    v = _get_vacancy(vacancy_id)
    graph = _get_graph(v)
    comp = _find_competency(graph, req.competency_id)

    try:
        updated = await ai_fix_competency(req.instruction, comp, v.description)
    except LLMError as exc:
        raise HTTPException(502, f"Ошибка AI: {exc}") from exc

    comp.skill = updated.skill

    return AiFixCompetencyResponse(
        status="ok", message="Компетенция обновлена AI", updated=comp
    )


# ---------------------------------------------------------------------------
# Sub-competencies
# ---------------------------------------------------------------------------


@app.put("/api/vacancies/{vacancy_id}/sub-competency")
async def update_sub_competency(
    vacancy_id: str, req: UpdateSubCompetencyRequest
) -> dict:
    graph = _get_graph(_get_vacancy(vacancy_id))
    comp = _find_competency(graph, req.competency_id)
    sub = _find_sub(comp, req.sub_competency_id)

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
    graph = _get_graph(_get_vacancy(vacancy_id))
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
    graph = _get_graph(_get_vacancy(vacancy_id))
    comp = _find_competency(graph, req.competency_id)

    before = len(comp.sub_competencies)
    comp.sub_competencies = [
        s for s in comp.sub_competencies if s.id != req.sub_competency_id
    ]

    if len(comp.sub_competencies) == before:
        raise HTTPException(404, "Подкомпетенция не найдена")

    return StatusResponse(status="ok", message="Подкомпетенция удалена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix-sub", response_model=AiFixSubResponse)
async def ai_fix_sub_endpoint(
    vacancy_id: str, req: AiFixSubRequest
) -> AiFixSubResponse:
    v = _get_vacancy(vacancy_id)
    graph = _get_graph(v)
    comp = _find_competency(graph, req.competency_id)
    sub = _find_sub(comp, req.sub_competency_id)

    try:
        updated = await ai_fix_sub_competency(req.instruction, sub, v.description)
    except LLMError as exc:
        raise HTTPException(502, f"Ошибка AI: {exc}") from exc

    sub.name = updated.name
    sub.level = updated.level
    sub.description = updated.description
    sub.sub_skills = updated.sub_skills

    return AiFixSubResponse(
        status="ok", message="Подкомпетенция обновлена AI", updated=sub
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
