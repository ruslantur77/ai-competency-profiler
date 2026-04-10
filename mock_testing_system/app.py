from __future__ import annotations

import hashlib
import os
import random
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, TypedDict

from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

GENERATOR_VERSION = "v2"
DEFAULT_SEED = "mock-testing-system"
CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")


class ExternalTask(BaseModel):
    external_id: str
    title: str
    description: str
    type: str = Field(pattern="^(code|test)$")
    tags: list[str]
    created_at: datetime


class TaskBlueprint(TypedDict):
    title: str
    description: str
    tags: list[str]
    type: Literal["code", "test"]
    difficulty: Literal["junior", "middle"]


class ExtraTasksState(BaseModel):
    extra_tasks_count: int = Field(ge=0)


TASK_BLUEPRINTS: list[TaskBlueprint] = [
    {
        "title": "Реализовать CRUD для заметок на FastAPI",
        "description": "Добавьте эндпоинты создания, чтения, обновления и удаления заметок с валидацией входных данных и единым форматом ошибок.",
        "tags": ["python", "fastapi", "rest", "crud"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Сделать пагинацию и сортировку списка заказов",
        "description": "Реализуйте limit/offset, сортировку по дате и цене, а также ограничения на максимальный размер страницы.",
        "tags": ["python", "fastapi", "pagination", "sql"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Добавить JWT-аутентификацию в API",
        "description": "Реализуйте выдачу access/refresh токенов, проверку подписи и защиту приватных ручек.",
        "tags": ["python", "jwt", "auth", "security"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Вынести долгую обработку в фоновые задачи",
        "description": "Перенесите тяжелую операцию в фоновый воркер и верните клиенту идентификатор задачи для отслеживания статуса.",
        "tags": ["python", "fastapi", "asyncio", "background"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Собрать транзакционный сервис оплаты",
        "description": "Реализуйте сохранение платежа и связанных сущностей в одной транзакции с корректным rollback при ошибке.",
        "tags": ["python", "sqlalchemy", "transactions", "postgres"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Добавить кэширование карточки пользователя",
        "description": "Кэшируйте ответ в Redis, добавьте TTL и инвалидацию кэша при изменении профиля.",
        "tags": ["python", "redis", "caching", "backend"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Защитить обработчик webhook от дублей",
        "description": "Реализуйте идемпотентность по event_id, проверку подписи и безопасную повторную обработку.",
        "tags": ["python", "webhook", "idempotency", "security"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Реализовать rate limit middleware",
        "description": "Ограничьте частоту запросов по IP и пользователю, возвращайте корректный ответ при превышении лимита.",
        "tags": ["python", "fastapi", "middleware", "ratelimit"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Добавить загрузку файлов с проверками",
        "description": "Реализуйте прием файлов, проверку расширения и размера, а также безопасное имя сохранения.",
        "tags": ["python", "fastapi", "validation", "files"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Настроить Celery-задачу с ретраями",
        "description": "Сделайте задачу с экспоненциальным backoff, ограничением числа повторов и логированием причины отказа.",
        "tags": ["python", "celery", "retries", "queues"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Собрать модуль конфигурации через Pydantic Settings",
        "description": "Опишите переменные окружения, значения по умолчанию и валидацию обязательных параметров приложения.",
        "tags": ["python", "pydantic", "settings", "config"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Добавить корреляционный id в логи",
        "description": "Прокиньте request_id через middleware и включите его в структурированные логи всех слоев сервиса.",
        "tags": ["python", "logging", "middleware", "observability"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Подготовить миграцию с безопасным откатом",
        "description": "Добавьте миграцию схемы БД и отдельный downgrade, чтобы откат не ломал существующие данные.",
        "tags": ["python", "alembic", "postgres", "migrations"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Реализовать оптимистическую блокировку записи",
        "description": "Добавьте version field и проверку конфликтов обновления для защиты от race condition.",
        "tags": ["python", "sqlalchemy", "concurrency", "postgres"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Добавить версионирование API",
        "description": "Реализуйте маршруты v1/v2 и стратегию обратной совместимости на уровне схем ответов.",
        "tags": ["python", "fastapi", "rest", "versioning"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Сделать endpoint импорта CSV",
        "description": "Реализуйте парсинг CSV, валидацию строк и пакетную запись в БД с отчетом по ошибкам.",
        "tags": ["python", "fastapi", "csv", "validation"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Рефакторинг сервиса в repository pattern",
        "description": "Разделите слой доменной логики и доступ к данным через репозитории с четкими интерфейсами.",
        "tags": ["python", "architecture", "repository", "backend"],
        "type": "code",
        "difficulty": "middle",
    },
    {
        "title": "Улучшить healthcheck зависимостей",
        "description": "Добавьте проверку доступности БД и Redis, а также отдельные статусы liveness/readiness.",
        "tags": ["python", "fastapi", "healthcheck", "redis"],
        "type": "code",
        "difficulty": "junior",
    },
    {
        "title": "Написать unit-тесты для сервиса заказов",
        "description": "Покройте позитивные и негативные сценарии бизнес-логики с моками репозитория и внешних зависимостей.",
        "tags": ["python", "pytest", "unit-test", "mocks"],
        "type": "test",
        "difficulty": "junior",
    },
    {
        "title": "Покрыть интеграционными тестами API пользователей",
        "description": "Проверьте регистрацию, авторизацию и обновление профиля на тестовой БД с реальными запросами.",
        "tags": ["python", "pytest", "integration-test", "fastapi"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Сделать параметризованные тесты валидации схем",
        "description": "Проверьте граничные значения и некорректные payload для входных DTO с помощью pytest.mark.parametrize.",
        "tags": ["python", "pytest", "validation", "pydantic"],
        "type": "test",
        "difficulty": "junior",
    },
    {
        "title": "Протестировать gateway внешней системы",
        "description": "Напишите тесты HTTP-клиента с мок-транспортом, проверив query-параметры периода и обработку ошибок.",
        "tags": ["python", "pytest", "httpx", "contract-test"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Проверить rollback транзакций при исключении",
        "description": "Смоделируйте отказ в середине операции и убедитесь, что данные в БД остаются консистентными.",
        "tags": ["python", "pytest", "transactions", "postgres"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Покрыть async-эндпоинт тестами конкурентных запросов",
        "description": "Проверьте корректность ответа и отсутствие гонок при параллельных вызовах одного ресурса.",
        "tags": ["python", "pytest", "asyncio", "concurrency"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Написать тесты refresh-token сценария",
        "description": "Проверьте выпуск новой пары токенов, отзыв старого refresh и защиту от повторного использования.",
        "tags": ["python", "pytest", "jwt", "auth"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Проверить контракт пагинации",
        "description": "Добавьте тесты на limit/offset, сортировку и стабильность выдачи при одинаковых параметрах запроса.",
        "tags": ["python", "pytest", "contract-test", "pagination"],
        "type": "test",
        "difficulty": "junior",
    },
    {
        "title": "Покрыть тестами идемпотентность webhook",
        "description": "Проверьте, что повторное событие с тем же event_id не создает дубли и возвращает корректный ответ.",
        "tags": ["python", "pytest", "webhook", "idempotency"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Написать тесты инвалидации кэша",
        "description": "Проверьте, что после обновления сущности старое значение в Redis удаляется и читается новое.",
        "tags": ["python", "pytest", "redis", "caching"],
        "type": "test",
        "difficulty": "junior",
    },
    {
        "title": "Добавить smoke-тесты миграций",
        "description": "Проверьте цепочку upgrade/downgrade на чистой БД и валидность схемы после каждого шага.",
        "tags": ["python", "pytest", "alembic", "migrations"],
        "type": "test",
        "difficulty": "middle",
    },
    {
        "title": "Проверить API на базовую нагрузку",
        "description": "Подготовьте тестовый сценарий с небольшим параллелизмом и зафиксируйте время ответа для ключевых ручек.",
        "tags": ["python", "pytest", "performance", "api"],
        "type": "test",
        "difficulty": "middle",
    },
]

app = FastAPI(title="mock-testing-system", version="1.0.0")
app.state.extra_tasks_count = 0


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _ensure_utc(name: str, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{name}' must include timezone",
        )
    if value.utcoffset() != timedelta(0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{name}' must be UTC (Z)",
        )
    return value.astimezone(UTC)


def _check_auth(authorization: str | None) -> None:
    expected_token = os.getenv("TESTING_SYSTEM_API_TOKEN", "").strip()
    if not expected_token:
        return

    expected_value = f"Bearer {expected_token}"
    if authorization != expected_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )


def _build_seed(start: datetime, end: datetime) -> tuple[str, int]:
    configured_seed = os.getenv("MOCK_TESTING_SYSTEM_SEED", DEFAULT_SEED)
    key = f"{_utc_iso(start)}|{_utc_iso(end)}|{configured_seed}|{GENERATOR_VERSION}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return key, int.from_bytes(digest[:8], byteorder="big", signed=False)


def _build_rng(seed_key: str) -> random.Random:
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    seed_value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return random.Random(seed_value)


def _sample_count(rng: random.Random, start: datetime, end: datetime) -> int:
    duration_days = (end - start).total_seconds() / 86_400
    baseline = max(1, round(duration_days * 12))
    jitter = rng.randint(-4, 4)
    return max(1, min(500, baseline + jitter))


def _external_id(seed_key: str, index: int) -> str:
    value = hashlib.sha256(f"{seed_key}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"mock-task-{value}"


def _extra_external_id(seed_key: str, index: int) -> str:
    value = hashlib.sha256(f"{seed_key}|extra|{index}".encode("utf-8")).hexdigest()[:12]
    return f"mock-extra-task-{index}-{value}"


def _generate_task(
    *,
    seed_key: str,
    index: int,
    start: datetime,
    window_seconds: float,
    external_id: str,
) -> ExternalTask:
    rng = _build_rng(f"{seed_key}|item|{index}")
    blueprint = TASK_BLUEPRINTS[rng.randrange(len(TASK_BLUEPRINTS))]
    offset = rng.random() * window_seconds
    created_at = start + timedelta(seconds=offset)

    tags = list(blueprint["tags"])
    rng.shuffle(tags)
    selected_tags = sorted(tags[: rng.randint(2, min(4, len(tags)))])

    return ExternalTask(
        external_id=external_id,
        title=blueprint["title"],
        description=blueprint["description"],
        type=blueprint["type"],
        tags=selected_tags,
        created_at=created_at,
    )


def _generate_base_tasks(
    *,
    start: datetime,
    end: datetime,
    seed_key: str,
) -> list[ExternalTask]:
    rng = _build_rng(f"{seed_key}|base-count")
    count = _sample_count(rng, start, end)
    window_seconds = (end - start).total_seconds()

    tasks: list[ExternalTask] = []
    for index in range(count):
        tasks.append(
            _generate_task(
                seed_key=seed_key,
                index=index,
                start=start,
                window_seconds=window_seconds,
                external_id=_external_id(seed_key, index),
            )
        )

    return tasks


def _generate_extra_tasks(
    *,
    start: datetime,
    end: datetime,
    seed_key: str,
    extra_tasks_count: int,
) -> list[ExternalTask]:
    window_seconds = (end - start).total_seconds()

    tasks: list[ExternalTask] = []
    for index in range(extra_tasks_count):
        tasks.append(
            _generate_task(
                seed_key=f"{seed_key}|extra",
                index=index,
                start=start,
                window_seconds=window_seconds,
                external_id=_extra_external_id(seed_key, index),
            )
        )
    return tasks


def _deduplicate_external_ids(tasks: list[ExternalTask]) -> None:
    seen: dict[str, int] = {}
    for task in tasks:
        original = task.external_id
        count = seen.get(original, 0)
        if count:
            task.external_id = f"{original}-dup-{count}"
        seen[original] = count + 1


def _get_extra_tasks_count() -> int:
    return int(app.state.extra_tasks_count)


def _set_extra_tasks_count(value: int) -> int:
    app.state.extra_tasks_count = value
    return _get_extra_tasks_count()


def _generate_tasks(start: datetime, end: datetime) -> list[ExternalTask]:
    seed_key, _ = _build_seed(start, end)
    base_tasks = _generate_base_tasks(start=start, end=end, seed_key=seed_key)
    extra_tasks = _generate_extra_tasks(
        start=start,
        end=end,
        seed_key=seed_key,
        extra_tasks_count=_get_extra_tasks_count(),
    )
    tasks = [*base_tasks, *extra_tasks]
    _deduplicate_external_ids(tasks)
    tasks.sort(key=lambda item: (item.created_at, item.external_id))
    return tasks


@app.get("/internal/control/extra-tasks", response_model=ExtraTasksState)
async def get_extra_tasks_state() -> ExtraTasksState:
    return ExtraTasksState(extra_tasks_count=_get_extra_tasks_count())


@app.post("/internal/control/extra-tasks/set", response_model=ExtraTasksState)
async def set_extra_tasks_state(
    count: Annotated[int, Query(ge=0)],
) -> ExtraTasksState:
    value = _set_extra_tasks_count(count)
    return ExtraTasksState(extra_tasks_count=value)


@app.post("/internal/control/extra-tasks/reset", response_model=ExtraTasksState)
async def reset_extra_tasks_state() -> ExtraTasksState:
    value = _set_extra_tasks_count(0)
    return ExtraTasksState(extra_tasks_count=value)


@app.get("/external/tasks", response_model=list[ExternalTask])
async def list_external_tasks(
    start: Annotated[datetime, Query(...)],
    end: Annotated[datetime, Query(...)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> list[ExternalTask]:
    _check_auth(authorization)
    start_utc = _ensure_utc("start", start)
    end_utc = _ensure_utc("end", end)

    if end_utc <= start_utc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'end' must be greater than 'start'",
        )

    return _generate_tasks(start_utc, end_utc)
