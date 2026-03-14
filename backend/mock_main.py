# backend/main.py — ПОЛНЫЙ ФАЙЛ

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup
import copy
import re
import uuid

from mock_data import MOCK_GRAPH, MOCK_VACANCY_TEXT

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


# ===================== МОДЕЛИ =====================

# Вакансии
class CreateVacancyRequest(BaseModel):
    name: str
    description: str

class ImportHHRequest(BaseModel):
    url: str

class UpdateVacancyRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class VacancyListItem(BaseModel):
    id: str
    name: str
    status: str
    created_at: str

class GraphResponse(BaseModel):
    vacancy: dict
    categories: list[dict]
    competencies: list[dict]

# Категории
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

# Компетенции
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

# Подкомпетенции
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


# ===================== ВАКАНСИИ (CRUD) =====================

@app.get("/api/vacancies")
async def list_vacancies():
    """Список всех вакансий."""
    items = []
    for vid, vdata in vacancies_db.items():
        items.append({
            "id": vid,
            "name": vdata["name"],
            "status": vdata["status"],
            "created_at": vdata["created_at"],
        })
    return {"vacancies": items}


@app.post("/api/vacancies")
async def create_vacancy(req: CreateVacancyRequest):
    """Создание вакансии вручную."""
    from datetime import datetime

    vacancy_id = uuid.uuid4().hex[:8]

    vacancies_db[vacancy_id] = {
        "name": req.name,
        "description": req.description,
        "status": "extracting",  # extracting → ready
        "created_at": datetime.now().isoformat(),
        "graph": copy.deepcopy(MOCK_GRAPH),
        "hh_key_skills": [],
        "experience": "",
    }
    vacancies_db[vacancy_id]["graph"]["vacancy"]["name"] = req.name

    # Имитируем что через 3 секунды статус станет ready
    # В реальном приложении тут будет вызов LLM
    import threading
    def set_ready():
        if vacancy_id in vacancies_db:
            vacancies_db[vacancy_id]["status"] = "ready"

    threading.Timer(3.0, set_ready).start()

    return {
        "status": "ok",
        "vacancy": {
            "id": vacancy_id,
            "name": req.name,
            "status": "extracting",
            "created_at": vacancies_db[vacancy_id]["created_at"],
        },
    }


@app.post("/api/vacancies/import-hh")
async def import_from_hh(req: ImportHHRequest):
    """Импорт вакансии с hh.ru."""
    from datetime import datetime

    try:
        match = re.search(r'vacancy/(\d+)', req.url)
        if not match:
            match = re.search(r'(\d{6,})', req.url)

        if not match:
            raise HTTPException(400, "Не удалось извлечь ID вакансии из ссылки")

        hh_vacancy_id = match.group(1)
        hh_url = f"https://api.hh.ru/vacancies/{hh_vacancy_id}"
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

@app.get("/api/vacancies/{vacancy_id}/graph", response_model=GraphResponse)
async def get_graph(vacancy_id: str):
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

@app.put("/api/vacancies/{vacancy_id}/category")
async def update_category(vacancy_id: str, req: UpdateCategoryRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    for cat in vacancies_db[vacancy_id]["graph"]["categories"]:
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
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. (Моковый ответ)",
    }


# ===================== КОМПЕТЕНЦИИ =====================

@app.put("/api/vacancies/{vacancy_id}/competency")
async def update_competency(vacancy_id: str, req: UpdateCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

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
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. (Моковый ответ)",
    }


# ===================== ПОДКОМПЕТЕНЦИИ =====================

@app.put("/api/vacancies/{vacancy_id}/sub-competency")
async def update_sub_competency(vacancy_id: str, req: UpdateSubCompetencyRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    for comp in vacancies_db[vacancy_id]["graph"]["competencies"]:
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
            comp["sub_competencies"] = [s for s in comp["sub_competencies"] if s["id"] != req.sub_competency_id]
            if len(comp["sub_competencies"]) < original_len:
                return {"status": "ok", "message": "Подкомпетенция удалена"}

    raise HTTPException(404, "Не найдена")


@app.post("/api/vacancies/{vacancy_id}/ai-fix")
async def ai_fix_sub(vacancy_id: str, req: AiFixSubRequest):
    if vacancy_id not in vacancies_db:
        raise HTTPException(404, "Вакансия не найдена")

    return {
        "status": "ok",
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. (Моковый ответ)",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)