# Mock Testing System

Легкий внешний mock-сервис без БД для генерации задач по временному окну.

## API

`GET /external/tasks?start=<ISO-UTC>&end=<ISO-UTC>`

- `start`, `end` обязательны.
- Формат времени: ISO-8601 UTC (например, `2026-04-01T00:00:00Z`).
- Семантика окна: `[start, end)`.
- Детерминизм: одинаковый `start/end` возвращает одинаковый набор задач.

Ответ: JSON-массив задач с полями:
- `external_id`
- `title`
- `description`
- `type` (`code` или `test`)
- `tags`
- `created_at`

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
