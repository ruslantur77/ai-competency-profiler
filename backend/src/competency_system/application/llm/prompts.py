# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThreeStagePrompts:
    step1_categories: str
    step2_competencies: str
    step3_subcompetencies: str


@dataclass(frozen=True)
class LLMCodeAssessmentPrompts:
    prompt: str


class PromptCatalog:
    # TODO: move prompt storage and version management to DB.
    _VACANCY_PROMPTS: dict[str, ThreeStagePrompts] = {
        "v1": ThreeStagePrompts(
            step1_categories=(
                "Ты выбираешь релевантные категории компетенций для IT-вакансии.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенный top-level ключ: categories (список integer ID из available_categories).\n"
                "Включай только ID, релевантные вакансии. Не добавляй лишние ключи.\n\n"
                "Язык: если в ответе есть свободный текст, пиши преимущественно на русском.\n"
                "Общепринятые техтермины и названия технологий оставляй на английском "
                "(например: Python, FastAPI, REST API, PostgreSQL, JWT, SQL, async/await).\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Требования: Python, PostgreSQL, проектирование REST API.",\n'
                '  "available_categories": [\n'
                '    {"id": 1, "name": "Языки программирования"},\n'
                '    {"id": 2, "name": "Базы данных"},\n'
                '    {"id": 3, "name": "Soft Skills"},\n'
                '    {"id": 4, "name": "Мобильная разработка"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                '{"categories": [1, 2, 3]}'
            ),
            step2_competencies=(
                "Ты выбираешь релевантные компетенции внутри заданной категории для IT-вакансии.\n"
                "Также можешь предложить новые компетенции, если они важны, но отсутствуют в списке.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенные top-level ключи:\n"
                "  - competencies: list of integer IDs from available_competencies\n"
                "  - suggested_new: list of new competency objects with fields: "
                "name, description, is_required (bool), weight (0..1), reason\n"
                "Не добавляй лишние ключи.\n\n"
                "Язык полей suggested_new.name, suggested_new.description и suggested_new.reason:\n"
                "преимущественно русский; общепринятые техтермины и названия технологий оставляй "
                "на английском (Python, FastAPI, REST API, PostgreSQL, JWT, SQL, async/await).\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Требования: Python, PostgreSQL, проектирование REST API.",\n'
                '  "category": {"id": 1, "name": "Языки программирования"},\n'
                '  "available_competencies": [\n'
                '    {"id": 1, "name": "Python", "description": "Уверенное знание Core Python"},\n'
                '    {"id": 2, "name": "Java", "description": "Промышленная разработка на Java"},\n'
                '    {"id": 3, "name": "Go", "description": "Разработка сервисов на Go"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                "{\n"
                '  "competencies": [1],\n'
                '  "suggested_new": [\n'
                "    {\n"
                '      "name": "Async Python",\n'
                '      "description": "Практическое владение asyncio и async-фреймворками",\n'
                '      "is_required": false,\n'
                '      "weight": 0.6,\n'
                '      "reason": "Async Python часто нужен в современных backend-сервисах, но отсутствует в списке"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
            step3_subcompetencies=(
                "Ты выбираешь релевантные подкомпетенции внутри заданной компетенции для IT-вакансии.\n"
                "Также можешь предложить новые подкомпетенции, если они важны, но отсутствуют в списке.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенные top-level ключи:\n"
                "  - sub_competencies: list of objects with fields: llm_id (int), "
                "target_level (0..5), weight (0..1)\n"
                "  - suggested_new: list of new subcompetency objects with fields: "
                "name, description, target_level (0..5), weight (0..1), reason\n"
                "Не добавляй лишние ключи.\n\n"
                "Язык полей suggested_new.name, suggested_new.description и suggested_new.reason:\n"
                "преимущественно русский; общепринятые техтермины и названия технологий оставляй "
                "на английском (Python, FastAPI, REST API, PostgreSQL, JWT, SQL, async/await).\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Senior Python Backend Engineer. Требования: Python, PostgreSQL, проектирование REST API.",\n'
                '  "competency": {"id": 1, "name": "Python"},\n'
                '  "available_sub_competencies": [\n'
                '    {"id": 1, "name": "OOP", "description": "Объектно-ориентированное проектирование на Python"},\n'
                '    {"id": 2, "name": "Testing", "description": "pytest, unit и integration тесты"},\n'
                '    {"id": 3, "name": "Type hints", "description": "Использование модуля typing"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                "{\n"
                '  "sub_competencies": [\n'
                '    {"llm_id": 1, "target_level": 4, "weight": 0.5},\n'
                '    {"llm_id": 2, "target_level": 3, "weight": 0.3}\n'
                "  ],\n"
                '  "suggested_new": [\n'
                "    {\n"
                '      "name": "Async/Await",\n'
                '      "description": "Умение писать асинхронный код с asyncio",\n'
                '      "target_level": 3,\n'
                '      "weight": 0.2,\n'
                '      "reason": "Асинхронные паттерны ожидаются на senior-уровне, но не представлены в списке"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
        )
    }

    _TASK_PROMPTS: dict[str, ThreeStagePrompts] = {
        "v1": ThreeStagePrompts(
            step1_categories=(
                "Ты выбираешь релевантные категории компетенций для оценочного задания.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенный top-level ключ: categories (список integer IDs из available_categories).\n"
                "Включай только ID, релевантные заданию. Не добавляй лишние ключи.\n\n"
                "Язык: если в ответе есть свободный текст, пиши преимущественно на русском.\n"
                "Общепринятые техтермины и названия технологий оставляй на английском "
                "(например: Python, FastAPI, REST API, PostgreSQL, JWT, SQL, async/await).\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Реализовать REST API endpoint на Python, который принимает список чисел и возвращает их в отсортированном порядке.",\n'
                '  "available_categories": [\n'
                '    {"id": 1, "name": "Языки программирования"},\n'
                '    {"id": 2, "name": "Алгоритмы и структуры данных"},\n'
                '    {"id": 3, "name": "Базы данных"},\n'
                '    {"id": 4, "name": "Мобильная разработка"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                '{"categories": [1, 2]}'
            ),
            step2_competencies=(
                "Ты выбираешь релевантные компетенции внутри заданной категории для оценочного задания.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенный top-level ключ: competencies (список integer IDs из available_competencies).\n"
                "Не предлагай новые компетенции. Не добавляй лишние ключи.\n\n"
                "Язык: если в ответе есть свободный текст, пиши преимущественно на русском.\n"
                "Общепринятые техтермины и названия технологий оставляй на английском.\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Реализовать REST API endpoint на Python, который принимает список чисел и возвращает их в отсортированном порядке.",\n'
                '  "category": {"id": 1, "name": "Языки программирования"},\n'
                '  "available_competencies": [\n'
                '    {"id": 1, "name": "Python", "description": "Уверенное знание Core Python"},\n'
                '    {"id": 2, "name": "Java", "description": "Промышленная разработка на Java"},\n'
                '    {"id": 3, "name": "Go", "description": "Разработка сервисов на Go"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                '{"competencies": [1]}'
            ),
            step3_subcompetencies=(
                "Ты выбираешь релевантные подкомпетенции внутри заданной компетенции для оценочного задания.\n"
                "Вывод ДОЛЖЕН быть одним JSON-объектом и ничем больше: без markdown и без пояснений.\n"
                "Разрешенный top-level ключ: sub_competencies (list of objects with fields: "
                "llm_id (int), weight (0..1)).\n"
                "Не предлагай новые подкомпетенции. Не добавляй лишние ключи.\n\n"
                "Язык: если в ответе есть свободный текст, пиши преимущественно на русском.\n"
                "Общепринятые техтермины и названия технологий оставляй на английском.\n"
                "JSON-ключи и служебные поля не переводи.\n\n"
                "Пример входа:\n"
                "{\n"
                '  "task": "Реализовать REST API endpoint на Python, который принимает список чисел и возвращает их в отсортированном порядке.",\n'
                '  "competency": {"id": 1, "name": "Python"},\n'
                '  "available_sub_competencies": [\n'
                '    {"id": 1, "name": "OOP", "description": "Объектно-ориентированное проектирование на Python"},\n'
                '    {"id": 2, "name": "Testing", "description": "pytest, unit и integration тесты"},\n'
                '    {"id": 3, "name": "Type hints", "description": "Использование модуля typing"}\n'
                "  ]\n"
                "}\n\n"
                "Пример выхода:\n"
                "{\n"
                '  "sub_competencies": [\n'
                '    {"llm_id": 1, "weight": 0.4},\n'
                '    {"llm_id": 3, "weight": 0.6}\n'
                "  ]\n"
                "}"
            ),
        )
    }

    _CODE_ASSESSMENT_PROMPTS: dict[str, LLMCodeAssessmentPrompts] = {
        "v1": LLMCodeAssessmentPrompts(
            prompt=(
                "Оцени присланный код относительно требований задания. "
                "Верни JSON с полями: passed, score, feedback, feedback_items.\n"
                "feedback_items должен быть массивом объектов: "
                "{type: 'positive'|'negative', value: string, position: integer}.\n"
                "Поля feedback и feedback_items[].value пиши преимущественно на русском.\n"
                "Общепринятые техтермины и названия технологий оставляй на английском "
                "(например: Python, FastAPI, REST API, PostgreSQL, JWT, SQL, async/await).\n"
                "JSON-ключи, типы и служебные поля не переводи.\n"
                "Используй фиксированные критерии:\n"
                "- Корректность относительно задачи и переданных тестов\n"
                "- Качество и читаемость кода\n"
                "- Алгоритмическая и структурная эффективность\n"
                "- Надежность и обработка edge cases\n"
                "- Диапазон score: 0..100."
            )
        )
    }

    def get_vacancy_prompts(self, version: str) -> ThreeStagePrompts:
        prompts = self._VACANCY_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown vacancy prompt version: {version}")
        return prompts

    def get_task_prompts(self, version: str) -> ThreeStagePrompts:
        prompts = self._TASK_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown task prompt version: {version}")
        return prompts

    def get_code_assessment_prompts(self, version: str) -> LLMCodeAssessmentPrompts:
        prompts = self._CODE_ASSESSMENT_PROMPTS.get(version)
        if prompts is None:
            raise ValueError(f"Unknown code assessment prompt version: {version}")
        return prompts
