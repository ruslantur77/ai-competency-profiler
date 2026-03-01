import copy
import re
import uuid

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from mock_data import MOCK_GRAPH, MOCK_VACANCY_TEXT

from .schemas import (
    AddCategoryRequest,
    AddCompetencyRequest,
    AddSubCompetencyRequest,
    AiFixCategoryRequest,
    AiFixCompetencyRequest,
    AiFixSubRequest,
    DeleteCategoryRequest,
    DeleteCompetencyRequest,
    DeleteSubCompetencyRequest,
    GraphResponse,
    UpdateCategoryRequest,
    UpdateCompetencyRequest,
    UpdateSubCompetencyRequest,
    VacancyRequest,
    VacancyResponse,
)

app = FastAPI(title="Competency Profiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище в памяти
vacancies_db = {}


@app.post("/api/vacancy/parse", response_model=VacancyResponse)
async def parse_vacancy(req: VacancyRequest):
    """Принимает ссылку на вакансию hh.ru, парсит и возвращает текст + метаданные."""
    vacancy_data = None

    try:
        match = re.search(r"vacancy/(\d+)", req.url)
        if not match:
            match = re.search(r"(\d{6,})", req.url)

        if match:
            vacancy_id = match.group(1)
            hh_url = f"https://api.hh.ru/vacancies/{vacancy_id}"
            headers = {"User-Agent": "CompetencyProfiler/1.0"}
            resp = requests.get(hh_url, headers=headers, timeout=10)

        if resp.status_code != 200:
            raise HTTPException(400, f"hh.ru вернул ошибку: {resp.status_code}")

        data = resp.json()
        soup = BeautifulSoup(data.get("description", ""), "html.parser")
        clean_text = soup.get_text(separator="\n").strip()

        return {
            "status": "ok",
            "name": data.get("name", ""),
            "description": clean_text,
            "experience": data.get("experience", {}).get("name", ""),
            "key_skills": [s["name"] for s in data.get("key_skills", [])],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Ошибка импорта: {str(e)}")


@app.get("/api/vacancies/{vacancy_id}")
async def get_vacancy(vacancy_id: str):
    """Получение данных вакансии."""
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    vdata = vacancies_db[vacancy_id]
    return {
        "id": vacancy_id,
        "name": vdata["name"],
        "description": vdata["description"],
        "status": vdata["status"],
        "created_at": vdata["created_at"],
        "experience": vdata.get("experience", ""),
        "key_skills": vdata.get("hh_key_skills", []),
    }


@app.put("/api/vacancies/{vacancy_id}")
async def update_vacancy(vacancy_id: str, req: UpdateVacancyRequest):
    """Обновление названия/описания вакансии."""
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    if req.name is not None:
        vacancies_db[vacancy_id]["name"] = req.name
        vacancies_db[vacancy_id]["graph"]["vacancy"]["name"] = req.name
    if req.description is not None:
        vacancies_db[vacancy_id]["description"] = req.description

    return {"status": "ok", "message": "Вакансия обновлена"}


@app.delete("/api/vacancies/{vacancy_id}")
async def delete_vacancy(vacancy_id: str):
    """Удаление вакансии."""
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    del vacancies_db[vacancy_id]
    return {"status": "ok", "message": "Вакансия удалена"}


@app.get("/api/vacancies/{vacancy_id}/status")
async def get_vacancy_status(vacancy_id: str):
    """Проверка статуса извлечения компетенций."""
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    return {"status": vacancies_db[vacancy_id]["status"]}


# ===================== ГРАФ =====================


@app.get("/api/graph/{session_id}", response_model=GraphResponse)
async def get_graph(session_id: str):
    """Возвращает граф компетенций."""
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    graph = vacancies_db[vacancy_id]["graph"]
    return GraphResponse(
        vacancy=graph["vacancy"],
        categories=graph["categories"],
        competencies=graph["competencies"],
    )


# ===================== КАТЕГОРИИ =====================


@app.put("/api/graph/{session_id}/category")
async def update_category(session_id: str, req: UpdateCategoryRequest):
    """Обновление категории."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    for cat in graph["categories"]:
        if cat["id"] == req.category_id:
            if req.name is not None:
                cat["name"] = req.name
            if req.emoji is not None:
                cat["emoji"] = req.emoji
            if req.description is not None:
                cat["description"] = req.description
            return {"status": "ok", "message": f"Категория '{cat['name']}' обновлена", "updated": cat}

    raise HTTPException(404, "Категория не найдена")


@app.post("/api/vacancies/{vacancy_id}/category")
async def add_category(vacancy_id: str, req: AddCategoryRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    new_cat = {
        "id": f"cat_{uuid.uuid4().hex[:6]}",
        "name": req.name,
        "emoji": req.emoji,
        "description": req.description,
    }
    vacancies_db[vacancy_id]["graph"]["categories"].append(new_cat)
    return {"status": "ok", "message": f"Категория '{req.name}' добавлена", "created": new_cat}


@app.delete("/api/vacancies/{vacancy_id}/category")
async def delete_category(vacancy_id: str, req: DeleteCategoryRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    graph = vacancies_db[vacancy_id]["graph"]
    original_len = len(graph["categories"])
    graph["categories"] = [c for c in graph["categories"] if c["id"] != req.category_id]

    if len(graph["categories"]) < original_len:
        graph["competencies"] = [c for c in graph["competencies"] if c["category_id"] != req.category_id]
        return {"status": "ok", "message": "Категория удалена"}

    raise HTTPException(404, "Категория не найдена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix-category")
async def ai_fix_category(vacancy_id: str, req: AiFixCategoryRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    return {
        "status": "ok",
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. "
        f"Категория будет обновлена. (Моковый ответ — LLM пока не подключена)",
        "ai_suggestion": {
            "name": "[AI] Обновлённая категория",
            "emoji": "🔮",
            "description": f"Сгенерировано AI: {req.instruction}",
        },
    }


@app.put("/api/graph/{session_id}/competency")
async def update_competency(session_id: str, req: UpdateCompetencyRequest):
    """Обновление компетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    for comp in vacancies_db[vacancy_id]["graph"]["competencies"]:
        if comp["id"] == req.competency_id:
            if req.skill is not None:
                comp["skill"] = req.skill
            if req.category_id is not None:
                comp["category_id"] = req.category_id
            return {"status": "ok", "message": "Компетенция обновлена", "updated": comp}

    raise HTTPException(404, "Компетенция не найдена")


@app.post("/api/vacancies/{vacancy_id}/competency")
async def add_competency(vacancy_id: str, req: AddCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    graph = vacancies_db[vacancy_id]["graph"]
    cat_exists = any(c["id"] == req.category_id for c in graph["categories"])
    if not cat_exists:
        raise HTTPException(404, "Категория не найдена")

    new_comp = {
        "id": f"comp_{uuid.uuid4().hex[:6]}",
        "category_id": req.category_id,
        "skill": req.skill,
        "sub_competencies": [],
    }
    graph["competencies"].append(new_comp)
    return {"status": "ok", "message": f"'{req.skill}' добавлена", "created": new_comp}


@app.delete("/api/vacancies/{vacancy_id}/competency")
async def delete_competency(vacancy_id: str, req: DeleteCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    graph = vacancies_db[vacancy_id]["graph"]
    original_len = len(graph["competencies"])
    graph["competencies"] = [c for c in graph["competencies"] if c["id"] != req.competency_id]

    if len(graph["competencies"]) < original_len:
        return {"status": "ok", "message": "Компетенция удалена"}

    raise HTTPException(404, "Компетенция не найдена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix-competency")
async def ai_fix_competency_full(vacancy_id: str, req: AiFixCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    return {
        "status": "ok",
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. "
        f"Компетенция будет обновлена. (Моковый ответ — LLM пока не подключена)",
        "ai_suggestion": {
            "skill": "[AI] Обновлённая компетенция",
            "sub_competencies": [
                {
                    "id": f"sub_{uuid.uuid4().hex[:6]}",
                    "name": "AI подкомпетенция 1",
                    "level": "intermediate",
                    "description": f"Сгенерировано AI: {req.instruction}",
                    "sub_skills": ["AI навык 1", "AI навык 2"],
                }
            ],
        },
    }


# ===================== ПОДКОМПЕТЕНЦИИ =====================


@app.put("/api/graph/{session_id}/sub-competency")
async def update_sub_competency(session_id: str, req: UpdateSubCompetencyRequest):
    """Обновление подкомпетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    for comp in graph["competencies"]:
        if comp["id"] == req.competency_id:
            for sub in comp["sub_competencies"]:
                if sub["id"] == req.sub_competency_id:
                    if req.name is not None:
                        sub["name"] = req.name
                    if req.level is not None:
                        sub["level"] = req.level
                    if req.description is not None:
                        sub["description"] = req.description
                    if req.sub_skills is not None:
                        sub["sub_skills"] = req.sub_skills
                    return {"status": "ok", "message": f"'{sub['name']}' обновлена", "updated": sub}

    raise HTTPException(404, "Не найдена")


@app.post("/api/vacancies/{vacancy_id}/sub-competency")
async def add_sub_competency(vacancy_id: str, req: AddSubCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    for comp in vacancies_db[vacancy_id]["graph"]["competencies"]:
        if comp["id"] == req.competency_id:
            new_sub = {
                "id": f"sub_{uuid.uuid4().hex[:6]}",
                "name": req.name,
                "level": req.level,
                "description": req.description,
                "sub_skills": req.sub_skills,
            }
            comp["sub_competencies"].append(new_sub)
            return {"status": "ok", "message": f"'{req.name}' добавлена", "created": new_sub}

    raise HTTPException(404, "Компетенция не найдена")


@app.delete("/api/vacancies/{vacancy_id}/sub-competency")
async def delete_sub_competency(vacancy_id: str, req: DeleteSubCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    for comp in vacancies_db[vacancy_id]["graph"]["competencies"]:
        if comp["id"] == req.competency_id:
            original_len = len(comp["sub_competencies"])
            comp["sub_competencies"] = [
                s for s in comp["sub_competencies"] if s["id"] != req.sub_competency_id
            ]
            if len(comp["sub_competencies"]) < original_len:
                return {"status": "ok", "message": "Подкомпетенция удалена"}

    raise HTTPException(404, "Не найдена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix")
async def ai_fix_sub(vacancy_id: str, req: AiFixSubRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    return {
        "status": "ok",
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. "
        f"Подкомпетенция будет обновлена. (Моковый ответ — LLM пока не подключена)",
        "ai_suggestion": {
            "id": req.sub_competency_id or f"sub_{uuid.uuid4().hex[:6]}",
            "name": "[AI] Обновлённая подкомпетенция",
            "level": "intermediate",
            "description": f"Сгенерировано AI по инструкции: {req.instruction}",
            "sub_skills": ["AI навык 1", "AI навык 2", "AI навык 3"],
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
