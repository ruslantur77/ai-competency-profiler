# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup
import copy
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

class VacancyRequest(BaseModel):
    url: str

class VacancyResponse(BaseModel):
    session_id: str
    vacancy_name: str
    vacancy_text: str
    experience: str
    key_skills: list[str]

class SubCompetency(BaseModel):
    id: str
    name: str
    level: str
    description: str
    sub_skills: list[str]

class Competency(BaseModel):
    id: str
    category_id: str
    skill: str
    sub_competencies: list[SubCompetency]

class Category(BaseModel):
    id: str
    name: str
    emoji: str
    description: str

class GraphResponse(BaseModel):
    vacancy: dict
    categories: list[dict]
    competencies: list[dict]

class UpdateSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str
    name: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    sub_skills: Optional[list[str]] = None

class DeleteSubCompetencyRequest(BaseModel):
    competency_id: str
    sub_competency_id: str

class AddSubCompetencyRequest(BaseModel):
    competency_id: str
    name: str
    level: str = "intermediate"
    description: str = ""
    sub_skills: list[str] = []

class AiFixRequest(BaseModel):
    competency_id: str
    sub_competency_id: Optional[str] = None
    instruction: str


# ===================== ЭНДПОИНТЫ =====================

@app.post("/api/vacancy/parse", response_model=VacancyResponse)
async def parse_vacancy(req: VacancyRequest):
    """
    Принимает ссылку на вакансию hh.ru,
    парсит и возвращает текст + метаданные.
    Создаёт сессию.
    """
    # Пытаемся реально спарсить
    vacancy_data = None

    try:
        # Извлекаем ID
        import re
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

    # Если не удалось — моковые данные
    if not vacancy_data:
        vacancy_data = {
            "name": MOCK_GRAPH["vacancy"]["name"],
            "text": MOCK_VACANCY_TEXT,
            "experience": MOCK_GRAPH["vacancy"]["experience"],
            "key_skills": MOCK_GRAPH["vacancy"]["key_skills"],
        }

    # Создаём сессию
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "vacancy": vacancy_data,
        "graph": copy.deepcopy(MOCK_GRAPH),
    }

    # Подменяем данные вакансии в графе
    sessions[session_id]["graph"]["vacancy"]["name"] = vacancy_data["name"]

    return VacancyResponse(
        session_id=session_id,
        vacancy_name=vacancy_data["name"],
        vacancy_text=vacancy_data["text"],
        experience=vacancy_data["experience"],
        key_skills=vacancy_data["key_skills"],
    )


@app.get("/api/graph/{session_id}", response_model=GraphResponse)
async def get_graph(session_id: str):
    """Возвращает граф компетенций (JSON)"""
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    graph = sessions[session_id]["graph"]
    return GraphResponse(
        vacancy=graph["vacancy"],
        categories=graph["categories"],
        competencies=graph["competencies"],
    )


@app.put("/api/graph/{session_id}/sub-competency")
async def update_sub_competency(session_id: str, req: UpdateSubCompetencyRequest):
    """Обновление подкомпетенции (ручное редактирование экспертом)"""
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
                        "updated": sub
                    }

    raise HTTPException(404, "Компетенция или подкомпетенция не найдена")


@app.delete("/api/graph/{session_id}/sub-competency")
async def delete_sub_competency(session_id: str, req: DeleteSubCompetencyRequest):
    """Удаление подкомпетенции"""
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


@app.post("/api/graph/{session_id}/sub-competency")
async def add_sub_competency(session_id: str, req: AddSubCompetencyRequest):
    """Добавление подкомпетенции вручную"""
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
                "created": new_sub
            }

    raise HTTPException(404, "Компетенция не найдена")


@app.post("/api/graph/{session_id}/ai-fix")
async def ai_fix_competency(session_id: str, req: AiFixRequest):
    """
    Моковый эндпоинт — AI правка компетенции.
    В будущем тут будет вызов LLM.
    """
    if session_id not in sessions:
        raise HTTPException(404, "Сессия не найдена")

    # Пока просто возвращаем уведомление
    return {
        "status": "ok",
        "message": f"🤖 AI получил инструкцию: '{req.instruction}'. "
                   f"Компетенция {req.competency_id} будет обновлена. "
                   f"(Моковый ответ — LLM пока не подключена)",
        "ai_suggestion": {
            "id": req.sub_competency_id or f"sub_{uuid.uuid4().hex[:6]}",
            "name": f"[AI] Обновлённая подкомпетенция",
            "level": "intermediate",
            "description": f"Сгенерировано AI по инструкции: {req.instruction}",
            "sub_skills": ["AI навык 1", "AI навык 2", "AI навык 3"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)