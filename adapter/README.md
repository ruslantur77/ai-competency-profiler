
# Competency Adapter

Адаптер для интеграции LMS (система другой команды) с AI Competency Profiler.
Поллит прогресс пользователей из LMS каждый час и отправляет результаты 
в webhook нашей системы.

## Архитектура

```
[LMS другой команды] 
    ↓ GET /api/kontest/integration/users/progress (каждый час)
[Adapter] → SQLite (хранит состояние и события)
    ↓ POST /api/v1/webhook/task-completed
[AI Competency Profiler]
```

### Что конвертируется

| LMS | Наша система |
|-----|-------------|
| `cases` (задачи с кодом) | `TaskType.code` |
| `quizzes` (тесты/квизы) | `TaskType.test` |
| `lectures` | не обрабатываются |
| `exams` | не обрабатываются |

## Структура проекта

```
adapter/
├── .env.example          # пример конфига
├── .gitignore
├── pyproject.toml        # зависимости
├── main.py               # точка входа FastAPI
├── core/
│   ├── config.py         # настройки через pydantic-settings
│   └── logging.py        # настройка логгера
├── db/
│   ├── database.py       # инициализация SQLite
│   └── repository.py     # все запросы к БД
├── lms/
│   ├── client.py         # HTTP клиент к LMS
│   └── schemas.py        # Pydantic модели ответов LMS
├── competency/
│   ├── client.py         # HTTP клиент к нашему webhook
│   └── schemas.py        # DTO для webhook
├── pipeline/
│   ├── converter.py      # маппинг LMS → наш формат
│   └── poller.py         # логика поллинга и фоновый worker
└── api/
    └── routes.py         # FastAPI эндпоинты
```

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (менеджер пакетов)

## Установка

```bash
# 1. Клонировать репозиторий и перейти в папку адаптера
cd adapter

# 2. Установить зависимости (uv создаст .venv автоматически)
uv sync

# 3. Создать .env из примера
cp .env.example .env

# 4. Заполнить .env (см. раздел Конфигурация)
```

## Конфигурация

Заполни `.env` файл:

```env
# Токен от другой команды (они выдают статичный Bearer токен)
LMS_API_TOKEN=your_lms_token_here

# UUID вакансии из нашей системы (должна быть в статусе ready)
# Взять из GET /api/v1/vacancies?status_filter=ready
TARGET_VACANCY_ID=your_vacancy_uuid_here

# Секрет для webhook (из .env основного проекта — TESTING_SYSTEM_WEBHOOK_SECRET)
OUR_WEBHOOK_SECRET=your_webhook_secret_here
```

### Как найти TARGET_VACANCY_ID

1. Запусти основной проект
2. Открой `http://localhost:1000/docs`
3. `GET /api/v1/vacancies?status_filter=ready`
4. Скопируй `id` любой вакансии со статусом `ready`

## Запуск

```bash
# Разработка (с автоперезагрузкой при изменениях)
uv run uvicorn main:app --port 8001 --reload

# Продакшен
uv run python main.py
```

Адаптер запустится на `http://localhost:8001`

## API эндпоинты адаптера

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/health` | Проверка работоспособности |
| `GET` | `/api/status` | Статистика: сколько событий pending/sent/failed |
| `POST` | `/api/sync-now` | Запустить синхронизацию вручную |

### Пример ответа /api/status

```json
{
  "status": "ok",
  "db_stats": {
    "pending": 0,
    "sent": 3,
    "failed": 0,
    "last_sync": "2026-04-22T17:17:41.407685+00:00"
  }
}
```

## Как работает поллинг

1. При старте адаптер читает `last_sync` из SQLite
2. Если первый запуск — берёт данные за последние `INITIAL_LOOKBACK_DAYS` дней
3. Запрашивает прогресс всех пользователей из LMS за период
4. Новые события сохраняет в SQLite со статусом `pending`
5. Отправляет `pending` события в наш webhook
6. При успехе помечает `sent`, при ошибке — `failed`
7. Обновляет `last_sync`
8. Спит `POLL_INTERVAL_SECONDS` секунд и повторяет

### Идемпотентность

Каждое событие имеет уникальный `event_id`:
- Для кода: `case_{user_id}_{case_id}_{submission_id}`
- Для тестов: `quiz_{user_id}_{lecture_id}_{attempts_used}`

SQLite не даст записать дубль — поле `event_id` уникально.
Наша система тоже защищена от дублей и вернёт `409` если событие уже обработано.

### Retry

Если webhook недоступен — tenacity повторит отправку:
- Максимум `WEBHOOK_MAX_ATTEMPTS` попыток (default: 5)
- Задержка растёт экспоненциально: 2s → 4s → 8s → ... → 60s

## Предварительные требования в основной системе

**Важно!** Перед тем как адаптер сможет отправлять результаты, в основной 
системе должны существовать задачи с соответствующими `external_id`.

Задачи из LMS:
- `cases` → `task_external_id = str(case_id)` (например `"27"`)
- `quizzes` → `task_external_id = "quiz_{lecture_id}"` (например `"quiz_2"`)

Задачи можно добавить вручную через psql:

```sql
INSERT INTO tasks (id, external_id, title, description, type, status, created_at, updated_at)
VALUES 
    (gen_random_uuid(), '27', 'Название задачи', 'Описание', 'code', 'draft', now(), now()),
    (gen_random_uuid(), 'quiz_2', 'Квиз лекции 2', 'Описание', 'test', 'draft', now(), now());
```

## Сброс состояния (для отладки)

```bash
# Удалить БД адаптера (сбросит last_sync и все события)
del adapter_state.db  # Windows
rm adapter_state.db   # Linux/Mac

# Удалить события в основной системе
docker compose exec postgres psql -U postgres -d competency_db
```

```sql
DELETE FROM webhook_events WHERE candidate_external_id = '4';
DELETE FROM candidates WHERE external_id = '4';
```

