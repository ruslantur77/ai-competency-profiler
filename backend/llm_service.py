from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from schemas import (
    CategoryNode,
    CompetencyLevel,
    CompetencyNode,
    GraphResponse,
    SubCompetency,
    VacancyNode,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_API_KEY = "api key"
_BASE_URL = "https://openrouter.ai/api/v1"
_MODEL = "openai/gpt-oss-20b"
_SYSTEM_PROMPT = "Ты эксперт в HR компетенциях. Отвечай строго JSON."

_LLM_RETRIES = 3
_LLM_RETRY_DELAY = 1.0  # базовая задержка в секундах (умножается на номер попытки)

client = AsyncOpenAI(base_url=_BASE_URL, api_key=_API_KEY)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Ошибка при обращении к LLM или парсинге ответа."""


# ---------------------------------------------------------------------------
# LLM primitives
# ---------------------------------------------------------------------------


async def _call_llm(
    prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> str:
    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.error("Ошибка запроса к LLM: %s", exc, exc_info=True)
        raise LLMError(f"Ошибка запроса к LLM: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        logger.error(
            "LLM вернул пустой ответ. Prompt (первые 500 символов): %.500s", prompt
        )
        raise LLMError("LLM вернул пустой ответ")

    return content


def _parse_json(text: str) -> Any:
    original = text

    block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if block:
        text = block.group(1)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(
            "Не удалось распарсить JSON от LLM. Ошибка: %s\nСырой ответ:\n%s",
            exc,
            original,
        )
        raise LLMError(f"LLM вернул невалидный JSON: {exc}") from exc


async def _llm_json(
    prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    retries: int = _LLM_RETRIES,
) -> Any:
    """
    Вызывает LLM и парсит JSON-ответ.
    При ошибке парсинга или сети делает до `retries` попыток
    с линейно растущей задержкой (1с, 2с, 3с...).
    """
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            raw = await _call_llm(
                prompt, temperature=temperature, max_tokens=max_tokens
            )
            return _parse_json(raw)
        except LLMError as exc:
            last_exc = exc
            if attempt < retries:
                delay = _LLM_RETRY_DELAY * attempt
                logger.warning(
                    "Попытка %d/%d не удалась (%s). Повтор через %.1f с...",
                    attempt,
                    retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Все %d попытки исчерпаны. Последняя ошибка: %s",
                    retries,
                    exc,
                )

    raise LLMError(f"LLM не ответил корректно после {retries} попыток") from last_exc


# ---------------------------------------------------------------------------
# Typed LLM output schemas (internal)
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


async def _detect_categories(
    vacancy_name: str, vacancy_text: str
) -> _LLMCategoriesResult:
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
    data = await _llm_json(prompt)
    try:
        return _LLMCategoriesResult.model_validate(data)
    except ValidationError as exc:
        logger.error(
            "Pydantic-валидация категорий не прошла. Ошибка: %s\nДанные: %s",
            exc,
            data,
        )
        raise LLMError(f"Неожиданная структура ответа (категории): {exc}") from exc


# ---------------------------------------------------------------------------
# Step 2 – извлечение скиллов по категориям
# ---------------------------------------------------------------------------


async def _extract_skills(
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
    data = await _llm_json(prompt)
    result = {k: v for k, v in data.items() if isinstance(v, list)}

    if not result:
        logger.warning(
            "LLM вернул пустой skills_map для вакансии '%s'. Сырые данные: %s",
            vacancy_name,
            data,
        )

    return result


# ---------------------------------------------------------------------------
# Step 3 – батчевое раскрытие скиллов одной категории
# ---------------------------------------------------------------------------


async def _expand_skills_batch(
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
    data = await _llm_json(prompt, max_tokens=4000)
    try:
        batch = _LLMBatchExpansion.model_validate(data)
    except ValidationError as exc:
        logger.error(
            "Pydantic-валидация batch expansion не прошла для категории '%s'.\n"
            "Ошибка: %s\nДанные: %s",
            category_name,
            exc,
            data,
        )
        raise LLMError(
            f"Неожиданная структура ответа (batch expansion): {exc}"
        ) from exc

    returned_skills = {e.skill for e in batch.results}
    missing = set(skills) - returned_skills
    if missing:
        logger.warning(
            "LLM пропустил %d скилл(ов) в категории '%s': %s",
            len(missing),
            category_name,
            missing,
        )

    return batch.results


# ---------------------------------------------------------------------------
# AI Fix – реальные LLM-редакции
# ---------------------------------------------------------------------------


async def ai_fix_category(
    instruction: str,
    category: CategoryNode,
    vacancy_description: str,
) -> CategoryNode:
    prompt = f"""
Ты HR-эксперт. Пользователь хочет изменить категорию компетенций.

Текущая категория:
- Название: {category.name}
- Описание: {category.description}
- Эмодзи: {category.emoji}

Контекст вакансии:
{vacancy_description[:1500]}

Инструкция: "{instruction}"

Выполни инструкцию. Верни все поля категории (даже неизменённые).

Ответ в JSON:
{{
  "name": "название",
  "emoji": "эмодзи",
  "description": "описание"
}}
"""
    data = await _llm_json(prompt)
    return CategoryNode(
        id=category.id,
        name=data.get("name") or category.name,
        emoji=data.get("emoji") or category.emoji,
        description=data.get("description") or category.description,
    )


async def ai_fix_competency(
    instruction: str,
    comp: CompetencyNode,
    vacancy_description: str,
) -> CompetencyNode:
    prompt = f"""
Ты HR-эксперт. Пользователь хочет изменить компетенцию.

Текущая компетенция: "{comp.skill}"
Контекст вакансии: {vacancy_description[:1500]}
Инструкция: "{instruction}"

Верни обновлённое название компетенции.

Ответ в JSON:
{{
  "skill": "новое название"
}}
"""
    data = await _llm_json(prompt)
    skill = data.get("skill")
    if not skill or not isinstance(skill, str):
        logger.error(
            "ai_fix_competency: LLM не вернул поле 'skill'. Полученные данные: %s", data
        )
        raise LLMError("LLM не вернул название компетенции")

    return CompetencyNode(
        id=comp.id,
        category_id=comp.category_id,
        skill=skill,
        sub_competencies=comp.sub_competencies,
    )


async def ai_fix_sub_competency(
    instruction: str,
    sub: SubCompetency,
    vacancy_description: str,
) -> SubCompetency:
    prompt = f"""
Ты HR-эксперт. Пользователь хочет изменить подкомпетенцию.

Текущая подкомпетенция:
- Название: {sub.name}
- Уровень: {sub.level}
- Описание: {sub.description}
- Навыки: {json.dumps(sub.sub_skills, ensure_ascii=False)}

Контекст вакансии: {vacancy_description[:1500]}
Инструкция: "{instruction}"

Верни все поля подкомпетенции (даже неизменённые).
level должен быть одним из: beginner, intermediate, advanced.

Ответ в JSON:
{{
  "name": "название",
  "level": "beginner/intermediate/advanced",
  "description": "описание",
  "sub_skills": ["навык1", "навык2"]
}}
"""
    data = await _llm_json(prompt)
    return SubCompetency(
        id=sub.id,
        name=data.get("name") or sub.name,
        level=data.get("level") or sub.level,
        description=data.get("description") or sub.description,
        sub_skills=data.get("sub_skills") or sub.sub_skills,
    )


# ---------------------------------------------------------------------------
# Public API – сборка графа
# ---------------------------------------------------------------------------


class VacancyInput(BaseModel):
    name: str
    text: str


async def build_graph(vacancy: dict[str, str] | VacancyInput) -> GraphResponse:
    """
    Строит граф компетенций для вакансии.
    Шаги 1 и 2 последовательны (каждый следующий зависит от предыдущего).
    Шаг 3 (expand по категориям) выполняется параллельно через asyncio.gather.
    """
    if isinstance(vacancy, dict):
        vacancy = VacancyInput.model_validate(vacancy)

    logger.info("Начало построения графа для вакансии '%s'", vacancy.name)

    # 1. Категории
    categories_result = await _detect_categories(vacancy.name, vacancy.text)
    llm_categories = categories_result.categories
    logger.info("Определено %d категорий", len(llm_categories))

    # 2. Скиллы
    skills_map = await _extract_skills(vacancy.name, vacancy.text, llm_categories)
    total_skills = sum(len(v) for v in skills_map.values())
    logger.info("Извлечено %d скиллов по %d категориям", total_skills, len(skills_map))

    graph_categories: list[CategoryNode] = [
        CategoryNode(
            id=cat.id, name=cat.name, description=cat.description, emoji=cat.emoji
        )
        for cat in llm_categories
    ]

    # 3. Параллельное раскрытие скиллов по категориям
    async def _expand_category(cat: _LLMCategory) -> list[CompetencyNode]:
        skills = skills_map.get(cat.id, [])
        if not skills:
            logger.debug("Категория '%s' не имеет скиллов, пропускаем", cat.name)
            return []

        try:
            expansions = await _expand_skills_batch(skills, cat.name, vacancy.text)
        except LLMError:
            logger.exception(
                "Ошибка расширения скиллов для категории '%s' — "
                "подкомпетенции будут пустыми",
                cat.name,
            )
            expansions = []

        expansion_map = {e.skill: e for e in expansions}
        nodes: list[CompetencyNode] = []

        for skill in skills:
            if skill not in expansion_map:
                logger.debug(
                    "Скилл '%s' отсутствует в expansion_map категории '%s', "
                    "sub_competencies будут пустыми",
                    skill,
                    cat.name,
                )
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
            nodes.append(
                CompetencyNode(
                    id=f"comp_{uuid.uuid4().hex[:6]}",
                    category_id=cat.id,
                    skill=skill,
                    sub_competencies=sub_competencies,
                )
            )
        return nodes

    batches = await asyncio.gather(*[_expand_category(cat) for cat in llm_categories])
    graph_competencies: list[CompetencyNode] = [
        node for batch in batches for node in batch
    ]

    logger.info(
        "Граф построен: %d категорий, %d компетенций",
        len(graph_categories),
        len(graph_competencies),
    )

    return GraphResponse(
        vacancy=VacancyNode(name=vacancy.name),
        categories=graph_categories,
        competencies=graph_competencies,
    )
