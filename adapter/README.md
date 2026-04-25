# Competency Adapter

Сервис-адаптер между AI Competency Profiler и внешней LMS системой Kontest.

## Назначение

Адаптер изолирует backend от реальной внешней системы:
- Backend продолжает работать с привычным контрактом `GET /external/tasks`
- Адаптер сам общается с Kontest API, трансформирует данные и шлёт webhook-события в backend

## Архитектура

```
Airflow DAG
    ↓
Backend POST /api/v1/tasks/sync
    ↓
Адаптер GET /api/external/tasks        ← бэкенд думает что это mock
    ↓
Kontest GET /integration/courses/{id}  ← реальный LMS

Kontest GET /integration/users/progress
    ↓
Адаптер (polling worker)
    ↓
Backend POST /api/v1/webhook/task-completed
```

## Потоки данных

### Поток задач (northbound)
1. Airflow триггерит `POST /api/v1/tasks/sync` на бэкенде
2. Бэкенд дёргает `GET /api/external/tasks` на адаптере
3. Адаптер идёт в LMS за списком курсов и задач
4. Возвращает задачи в формате который ожидает бэкенд
5. Бэкенд сохраняет задачи и запускает LLM маппинг

### Поток прогресса (southbound)
1. Polling worker каждые N секунд идёт в LMS за прогрессом студентов
2. Конвертирует прогресс в события и сохраняет в outbox
3. Отправляет события в `POST /api/v1/webhook/task-completed`
4. Успешные помечает `sent`, неуспешные — `retry` или `dlq`

## Быстрый старт

### Требования
- Python 3.11+
- uv

### Установка

```bash
git clone <repo>
cd adapter
uv sync
```

### Конфигурация

```bash
cp .env.example .env
# Отредактируй .env
```

### Запуск

```bash
# Локально
uv run main.py

# Или через Docker
docker compose up adapter
```

## Конфигурация (.env)

| Переменная | Обязательная | Описание |
|-----------|-------------|----------|
| `SOURCE_BASE_URL` | ✅ | Базовый URL Kontest API |
| `SOURCE_API_TOKEN` | ✅ | Bearer токен для Kontest |
| `SOURCE_COURSE_IDS` | ✅ | ID курсов для синка (CSV или JSON) |
| `COURSE_VACANCY_MAP` | ✅ | Маппинг course_id → vacancy_id (JSON) |
| `BACKEND_WEBHOOK_URL` | ✅ | URL webhook эндпоинта бэкенда |
| `BACKEND_WEBHOOK_SECRET` | ❌ | Секрет для X-Webhook-Secret заголовка |
| `POLL_INTERVAL_SECONDS` | ❌ | Интервал поллинга (default: 3600) |
| `INITIAL_LOOKBACK_MINUTES` | ❌ | Глубина первого синка (default: 1440) |
| `WEBHOOK_MAX_ATTEMPTS` | ❌ | Макс попыток отправки (default: 5) |
| `DLQ_ENABLED` | ❌ | Включить DLQ (default: true) |
| `DB_PATH` | ❌ | Путь к SQLite файлу (default: adapter_state.db) |
| `ADAPTER_PORT` | ❌ | Порт адаптера (default: 8001) |

### Пример COURSE_VACANCY_MAP

```bash
# Один курс — одна вакансия
COURSE_VACANCY_MAP={"1": "40000000-0000-0000-0000-000000000001"}

# Несколько курсов
COURSE_VACANCY_MAP={"1": "40000000-0000-0000-0000-000000000001", "2": "40000000-0000-0000-0000-000000000002"}
```

## API

### Service API

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/status` | Статистика (counters, last_sync) |
| `POST` | `/api/sync-now` | Форс-запуск цикла поллинга |
| `GET` | `/api/dlq` | Список застрявших событий |
| `POST` | `/api/dlq/requeue` | Вернуть DLQ события в очередь |
| `GET` | `/api/debug/events` | Просмотр событий в БД |

### Northbound API (для бэкенда)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/external/tasks` | Список задач из LMS (контракт mock_testing_system) |

#### GET /api/external/tasks

```
GET /api/external/tasks?start=2026-01-01T00:00:00Z&end=2026-04-25T23:59:59Z&force=false
```

Ответ:
```json
[
  {
    "external_id": "course_1_case_1",
    "title": "Сложение двух чисел",
    "description": "...",
    "type": "code",
    "tags": ["course:1", "kind:case"],
    "created_at": "2026-04-21T10:23:22Z"
  },
  {
    "external_id": "course_1_quiz_2",
    "title": "Quiz: Основы ООП",
    "description": "Автосгенерированная задача по квизу lecture 2",
    "type": "test",
    "tags": ["course:1", "kind:quiz"],
    "created_at": "2026-04-21T10:23:22Z"
  }
]
```

## Форматы ID

### task_external_id
- Code задача: `course_{course_id}_case_{case_id}`
- Quiz задача: `course_{course_id}_quiz_{lecture_id}`

### event_id
- Code задача: `course_{course_id}_case_{case_id}_user_{user_id}_submission_{submission_id}`
- Quiz задача: `course_{course_id}_quiz_{lecture_id}_user_{user_id}_attempt_{attempts_used}`

## Статусы событий

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает отправки |
| `sent` | Успешно отправлено |
| `failed` | Ошибка, будет retry |
| `dlq` | Превышен лимит попыток |

## DLQ (Dead Letter Queue)

Событие попадает в DLQ если:
- Превышено `WEBHOOK_MAX_ATTEMPTS` попыток
- Получен 401/403 от бэкенда (конфигурационная ошибка)

Для повторной отправки:
```bash
curl -X POST http://localhost:8001/api/dlq/requeue
```

## База данных

SQLite файл `adapter_state.db` содержит:

| Таблица | Описание |
|---------|----------|
| `sync_state` | Watermark последнего синка |
| `events_outbox` | Outbox событий прогресса студентов |
| `course_cache` | Кэш задач из LMS |

## Проверка работоспособности

```bash
uv run test_main.py
```

## Интеграция с Airflow

В бэкенде настроить:
```bash
TESTING_SYSTEM_BASE_URL=http://adapter:8001/api
```

В Airflow UI добавить Connection:
| Поле | Значение |
|------|----------|
| Conn Id | `competency_adapter` |
| Conn Type | `HTTP` |
| Host | `http://adapter` |
| Port | `8001` |

DAG `task_sync` автоматически триггерит адаптер после синка задач.