from __future__ import annotations

import json
import re
import uuid
from typing import Any

from openai import OpenAI
from pydantic import BaseModel
from schemas import (
    CategoryNode,
    CompetencyLevel,
    CompetencyNode,
    GraphResponse,
    SubCompetency,
    VacancyNode,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_API_KEY = "api key"
_BASE_URL = "https://openrouter.ai/api/v1"
_MODEL = "openai/gpt-oss-20b"
_SYSTEM_PROMPT = "Ты эксперт в HR компетенциях. Отвечай строго JSON."

client = OpenAI(base_url=_BASE_URL, api_key=_API_KEY)


# ---------------------------------------------------------------------------
# LLM primitives
# ---------------------------------------------------------------------------


def _call_llm(prompt: str, *, temperature: float = 0.1, max_tokens: int = 2000) -> str:
    response = client.chat.completions.create(
        model=_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM вернул пустой ответ")
    return content


def _parse_json(text: str) -> Any:
    # Снимаем markdown-обёртку если есть
    block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if block:
        text = block.group(1)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group()

    return json.loads(text)


def _llm_json(prompt: str, *, temperature: float = 0.1, max_tokens: int = 2000) -> Any:
    raw = _call_llm(prompt, temperature=temperature, max_tokens=max_tokens)
    return _parse_json(raw)


# ---------------------------------------------------------------------------
# Typed LLM outputs
# ---------------------------------------------------------------------------


class _LLMCategory(BaseModel):
    id: str
    name: str
    description: str
    emoji: str


class _LLMCategoriesResult(BaseModel):
    profession: str
    categories: list[_LLMCategory]


class _LLMSubCompetency(BaseModel):
    name: str
    level: CompetencyLevel
    description: str
    sub_skills: list[str]


class _LLMSkillExpansion(BaseModel):
    skill: str
    sub_competencies: list[_LLMSubCompetency]


class _LLMBatchExpansion(BaseModel):
    results: list[_LLMSkillExpansion]


# ---------------------------------------------------------------------------
# Step 1 – определение категорий
# ---------------------------------------------------------------------------


def _detect_categories(vacancy_name: str, vacancy_text: str) -> _LLMCategoriesResult:
    prompt = f"""
Ты эксперт в профессиональных компетенциях и HR.

Вакансия: {vacancy_name}

Текст:
{vacancy_text[:3000]}

Определи 3-6 КАТЕГОРИЙ компетенций, которые релевантны именно для этой профессии.

Примеры для разных профессий (НЕ КОПИРУЙ, это только для понимания формата):
- Data Analyst: технические навыки, аналитические методы, доменные знания, soft skills
- Повар: кулинарные техники, знание продуктов, санитарные нормы, организация работы
- Водитель: навыки вождения, знание ПДД, техобслуживание, логистика, безопасность
- Контент-мейкер: создание контента, платформы и инструменты, аналитика, тренды

Определи категории именно для данной вакансии.

Для каждой категории дай:
- id: короткий ключ на английском (snake_case)
- name: название на русском
- description: что входит (1 предложение)
- emoji: подходящий эмодзи

Ответ в JSON:
{{
    "profession": "название профессии",
    "categories": [
        {{
            "id": "category_key",
            "name": "Название категории",
            "description": "Что сюда входит",
            "emoji": "🔧"
        }}
    ]
}}
"""
    data = _llm_json(prompt)
    return _LLMCategoriesResult.model_validate(data)


# ---------------------------------------------------------------------------
# Step 2 – извлечение скиллов по категориям
# ---------------------------------------------------------------------------


def _extract_skills(
    vacancy_name: str,
    vacancy_text: str,
    categories: list[_LLMCategory],
) -> dict[str, list[str]]:
    cats = "\n".join(f"{c.id}: {c.name} - {c.description}" for c in categories)
    template = "{\n" + ",\n".join(f'"{c.id}":["skill1"]' for c in categories) + "\n}"

    prompt = f"""
Ты HR-аналитик.

Вакансия: "{vacancy_name}"

Текст:
{vacancy_text[:4000]}

Извлеки ВСЕ конкретные требования к кандидату и обязанности.
Раздели по следующим категориям:

{cats}

Будь конкретен. Извлекай и то, что явно подразумевается в обязанностях.
Каждый скилл — отдельный пункт (не объединяй несколько в один).

Ответ строго в JSON:
{template}

Только JSON.
"""
    data = _llm_json(prompt)
    # data: dict[category_id, list[str]]
    return {k: v for k, v in data.items() if isinstance(v, list)}


# ---------------------------------------------------------------------------
# Step 3 – батчевое раскрытие скиллов одной категории
# ---------------------------------------------------------------------------


def _expand_skills_batch(
    skills: list[str],
    category_name: str,
    context: str,
) -> list[_LLMSkillExpansion]:
    skills_json = json.dumps(skills, ensure_ascii=False, indent=2)

    template = """{
  "results": [
    {
      "skill": "название skill из входа",
      "sub_competencies": [
        {
          "name": "подкомпетенция",
          "level": "beginner",
          "description": "описание",
          "sub_skills": ["skill1", "skill2"]
        }
      ]
    }
  ]
}"""

    prompt = f"""
Ты эксперт в профессиональном обучении.

Категория: {category_name}

Контекст вакансии:
{context[:3000]}

Ниже список компетенций:

{skills_json}

Для КАЖДОЙ компетенции разложи на 3-6 подкомпетенций.

Требования:
— не пропускай ни одной компетенции  
— порядок сохраняй  
— skill должен совпадать с входным текстом  

level: beginner / intermediate / advanced

Ответ строго JSON:

{template}

Только JSON.
"""
    data = _llm_json(prompt, max_tokens=4000)
    batch = _LLMBatchExpansion.model_validate(data)
    return batch.results


# ---------------------------------------------------------------------------
# Public API – сборка графа
# ---------------------------------------------------------------------------


class VacancyInput(BaseModel):
    name: str
    text: str


def build_graph(vacancy: dict[str, str] | VacancyInput) -> GraphResponse:
    """Основная точка входа. Принимает dict или VacancyInput, возвращает GraphResponse."""

    if isinstance(vacancy, dict):
        vacancy = VacancyInput.model_validate(vacancy)

    # 1. Категории
    categories_result = _detect_categories(vacancy.name, vacancy.text)
    llm_categories = categories_result.categories

    # 2. Скиллы
    skills_map = _extract_skills(vacancy.name, vacancy.text, llm_categories)

    graph_categories: list[CategoryNode] = []
    graph_competencies: list[CompetencyNode] = []

    for cat in llm_categories:
        graph_categories.append(
            CategoryNode(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                emoji=cat.emoji,
            )
        )

    # 3. Раскрытие скиллов батчем по категориям
    for cat in llm_categories:
        skills = skills_map.get(cat.id, [])
        if not skills:
            continue

        expansions = _expand_skills_batch(skills, cat.name, vacancy.text)
        expansion_map = {e.skill: e for e in expansions}

        for skill in skills:
            expansion = expansion_map.get(
                skill, _LLMSkillExpansion(skill=skill, sub_competencies=[])
            )

            sub_competencies = [
                SubCompetency(
                    id=f"sub_{uuid.uuid4().hex[:6]}",
                    name=s.name,
                    level=s.level,
                    description=s.description,
                    sub_skills=s.sub_skills,
                )
                for s in expansion.sub_competencies
            ]

            graph_competencies.append(
                CompetencyNode(
                    id=f"comp_{uuid.uuid4().hex[:6]}",
                    category_id=cat.id,
                    skill=skill,
                    sub_competencies=sub_competencies,
                )
            )

    return GraphResponse(
        vacancy=VacancyNode(name=vacancy.name),
        categories=graph_categories,
        competencies=graph_competencies,
    )
