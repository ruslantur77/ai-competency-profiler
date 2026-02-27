# backend/main.py

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

# Хранилище в памяти (моковое)
sessions = {}


# ===================== МОДЕЛИ =====================

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


# ===================== ВАКАНСИЯ =====================

@app.post("/api/vacancy/parse", response_model=VacancyResponse)
async def parse_vacancy(req: VacancyRequest):
    """Принимает ссылку на вакансию hh.ru, парсит и возвращает текст + метаданные."""
    vacancy_data = None

    try:
        match = re.search(r'vacancy/(\d+)', req.url)
        if not match:
            match = re.search(r'(\d{6,})', req.url)

        if match:
            vacancy_id = match.group(1)
            hh_url = f"https://api.hh.ru/vacancies/{vacancy_id}"
            headers = {"User-Agent": "CompetencyProfiler/1.0"}
            resp = requests.get(hh_url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                soup = BeautifulSoup(data.get("description", ""), "html.parser")
                clean_text = soup.get_text(separator="\n").strip()

                vacancy_data = {
                    "name": data.get("name", ""),
                    "text": clean_text,
                    "experience": data.get("experience", {}).get("name", ""),
                    "key_skills": [s["name"] for s in data.get("key_skills", [])],
                }
    except Exception:
        pass

    if not vacancy_data:
        vacancy_data = {
            "name": MOCK_GRAPH["vacancy"]["name"],
            "text": MOCK_VACANCY_TEXT,
            "experience": MOCK_GRAPH["vacancy"]["experience"],
            "key_skills": MOCK_GRAPH["vacancy"]["key_skills"],
        }

    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "vacancy": vacancy_data,
        "graph": copy.deepcopy(MOCK_GRAPH),
    }
    sessions[session_id]["graph"]["vacancy"]["name"] = vacancy_data["name"]

    return VacancyResponse(
        session_id=session_id,
        vacancy_name=vacancy_data["name"],
        vacancy_text=vacancy_data["text"],
        experience=vacancy_data["experience"],
        key_skills=vacancy_data["key_skills"],
    )


# ===================== ГРАФ =====================

@app.get("/api/graph/{session_id}", response_model=GraphResponse)
async def get_graph(session_id: str):
    """Возвращает граф компетенций."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]
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
            return {
                "status": "ok",
                "message": f"Категория '{cat['name']}' обновлена",
                "updated": cat,
            }

    raise HTTPException(404, "Категория не найдена")


@app.post("/api/graph/{session_id}/category")
async def add_category(session_id: str, req: AddCategoryRequest):
    """Добавление категории."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    new_cat = {
        "id": f"cat_{uuid.uuid4().hex[:6]}",
        "name": req.name,
        "emoji": req.emoji,
        "description": req.description,
    }
    graph["categories"].append(new_cat)

    return {
        "status": "ok",
        "message": f"Категория '{req.name}' добавлена",
        "created": new_cat,
    }


@app.delete("/api/graph/{session_id}/category")
async def delete_category(session_id: str, req: DeleteCategoryRequest):
    """Удаление категории и всех её компетенций."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    original_len = len(graph["categories"])
    graph["categories"] = [c for c in graph["categories"] if c["id"] != req.category_id]

    if len(graph["categories"]) < original_len:
        graph["competencies"] = [
            c for c in graph["competencies"] if c["category_id"] != req.category_id
        ]
        return {"status": "ok", "message": "Категория и все её компетенции удалены"}

    raise HTTPException(404, "Категория не найдена")


@app.post("/api/graph/{session_id}/ai-fix-category")
async def ai_fix_category(session_id: str, req: AiFixCategoryRequest):
    """AI правка категории (моковый)."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

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


# ===================== КОМПЕТЕНЦИИ =====================

@app.put("/api/graph/{session_id}/competency")
async def update_competency(session_id: str, req: UpdateCompetencyRequest):
    """Обновление компетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    for comp in graph["competencies"]:
        if comp["id"] == req.competency_id:
            if req.skill is not None:
                comp["skill"] = req.skill
            if req.category_id is not None:
                comp["category_id"] = req.category_id
            return {
                "status": "ok",
                "message": "Компетенция обновлена",
                "updated": comp,
            }

    raise HTTPException(404, "Компетенция не найдена")


@app.post("/api/graph/{session_id}/competency")
async def add_competency(session_id: str, req: AddCompetencyRequest):
    """Добавление компетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

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

    return {
        "status": "ok",
        "message": f"Компетенция '{req.skill}' добавлена",
        "created": new_comp,
    }


@app.delete("/api/graph/{session_id}/competency")
async def delete_competency(session_id: str, req: DeleteCompetencyRequest):
    """Удаление компетенции со всеми подкомпетенциями."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    original_len = len(graph["competencies"])
    graph["competencies"] = [
        c for c in graph["competencies"] if c["id"] != req.competency_id
    ]

    if len(graph["competencies"]) < original_len:
        return {"status": "ok", "message": "Компетенция удалена"}

    raise HTTPException(404, "Компетенция не найдена")


@app.post("/api/graph/{session_id}/ai-fix-competency")
async def ai_fix_competency_full(session_id: str, req: AiFixCompetencyRequest):
    """AI правка компетенции (моковый)."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

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
                    return {
                        "status": "ok",
                        "message": f"Подкомпетенция '{sub['name']}' обновлена",
                        "updated": sub,
                    }

    raise HTTPException(404, "Компетенция или подкомпетенция не найдена")


@app.post("/api/graph/{session_id}/sub-competency")
async def add_sub_competency(session_id: str, req: AddSubCompetencyRequest):
    """Добавление подкомпетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    for comp in graph["competencies"]:
        if comp["id"] == req.competency_id:
            new_sub = {
                "id": f"sub_{uuid.uuid4().hex[:6]}",
                "name": req.name,
                "level": req.level,
                "description": req.description,
                "sub_skills": req.sub_skills,
            }
            comp["sub_competencies"].append(new_sub)
            return {
                "status": "ok",
                "message": f"Подкомпетенция '{req.name}' добавлена",
                "created": new_sub,
            }

    raise HTTPException(404, "Компетенция не найдена")


@app.delete("/api/graph/{session_id}/sub-competency")
async def delete_sub_competency(session_id: str, req: DeleteSubCompetencyRequest):
    """Удаление подкомпетенции."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]

    for comp in graph["competencies"]:
        if comp["id"] == req.competency_id:
            original_len = len(comp["sub_competencies"])
            comp["sub_competencies"] = [
                s for s in comp["sub_competencies"]
                if s["id"] != req.sub_competency_id
            ]
            if len(comp["sub_competencies"]) < original_len:
                return {"status": "ok", "message": "Подкомпетенция удалена"}

    raise HTTPException(404, "Не найдена")


@app.post("/api/graph/{session_id}/ai-fix")
async def ai_fix_sub(session_id: str, req: AiFixSubRequest):
    """AI правка подкомпетенции (моковый)."""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

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