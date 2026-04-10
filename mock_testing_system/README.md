# Mock Testing System

Легкий внешний mock-сервис без БД для генерации задач по временному окну.

Контент генератора:
- минимум 30 уникальных шаблонов заданий;
- язык `title/description`: русский;
- домен: backend + python;
- распределение типов: `60% code / 40% test`;
- внутренние уровни сложности шаблонов: `junior`, `middle`.

## API

`GET /external/tasks?start=<ISO-UTC>&end=<ISO-UTC>`

- `start`, `end` обязательны.
- Формат времени: ISO-8601 UTC (например, `2026-04-01T00:00:00Z`).
- Семантика окна: `[start, end)`.
- Детерминизм: одинаковый `start/end` возвращает одинаковый набор задач.
- При смене версии генератора (внутренняя `GENERATOR_VERSION`) набор может измениться.

Ответ: JSON-массив задач с полями:
- `external_id`
- `title`
- `description`
- `type` (`code` или `test`)
- `tags`
- `created_at`

Примечание: уровень сложности используется только внутри генератора и не отдается в API.

## Runtime control (для демо backfill)

Сервис поддерживает in-memory счетчик добавочных задач для каждого окна:
- `GET /internal/control/extra-tasks` — текущее значение `extra_tasks_count`.
- `POST /internal/control/extra-tasks/set?count=<N>` — установить точное значение `N >= 0`.
- `POST /internal/control/extra-tasks/reset` — сбросить в `0`.

Поведение:
- при `extra_tasks_count = N` сервис добавляет `N` дополнительных задач в каждое окно `[start, end)`;
- базовые задачи не пропадают;
- `external_id` остаются уникальными;
- при неизменном `start/end` и `extra_tasks_count` ответ стабилен;
- состояние счетчика живет только в памяти процесса и сбрасывается после рестарта контейнера.

## Auth

Если задан `TESTING_SYSTEM_API_TOKEN`, сервис требует:

`Authorization: Bearer <TESTING_SYSTEM_API_TOKEN>`

Если токен пустой, авторизация не проверяется.

## Локальный запуск

```bash
cd mock_testing_system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

## Docker (ручной запуск)

```bash
cd mock_testing_system
docker build -t mock-testing-system .
docker run --rm -p 9000:9000 \
  -e TESTING_SYSTEM_API_TOKEN=dev-token \
  -e MOCK_TESTING_SYSTEM_SEED=seed-1 \
  mock-testing-system
```

## Пример запроса

```bash
curl -s "http://localhost:9000/external/tasks?start=2026-04-01T00:00:00Z&end=2026-04-02T00:00:00Z" \
  -H "Authorization: Bearer dev-token"
```

## Пример демо из запущенного контейнера

```bash
# 1) проверить текущее значение добавки
curl -s "http://127.0.0.1:9000/internal/control/extra-tasks"

# 2) установить +1 дополнительную задачу в каждое окно
curl -s -X POST "http://127.0.0.1:9000/internal/control/extra-tasks/set?count=1"

# 3) убедиться, что в том же окне появилась новая задача
curl -s "http://127.0.0.1:9000/external/tasks?start=2026-04-01T00:00:00Z&end=2026-04-02T00:00:00Z" \
  -H "Authorization: Bearer dev-token"

# 4) вернуть базовое состояние
curl -s -X POST "http://127.0.0.1:9000/internal/control/extra-tasks/reset"
```
