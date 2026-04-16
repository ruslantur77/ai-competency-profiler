# Frontend: AI Competency Profiler

SPA на React + Vite для управления вакансиями, графом компетенций, suggestions и ранжированием кандидатов.

## Быстрый старт

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
npm run lint
npm run build
```

## Конфигурация API

- Базовый URL по умолчанию: `/api/v1`.
- В dev используется Vite proxy (`/api -> http://localhost:1000`).
- В runtime можно задать `FRONTEND_API_BASE_URL`.

## Архитектура API-слоя

- Base axios + auth refresh interceptor: `src/api/base.js`
- Domain API modules:
  - `src/api/auth.js`
  - `src/api/vacancies.js`
  - `src/api/tasks.js`
  - `src/api/ranking.js`
  - `src/api/suggestions.js`
- Адаптеры ответов: `src/api/adapters.js`
- Централизованный mapping ошибок: `src/api/errors.js`
- Ролевые правила UI: `src/api/roles.js`
- Совместимость-баррель: `src/api/client.js` (re-export only)
- Legacy-заглушки: `src/api/legacy-stubs.js`

## Role visibility matrix

Источник роли пользователя: `GET /auth/me`.

| Feature | HR | EXPERT | ADMIN |
|---------|----|--------|-------|
| Vacancies list/read | ✅ | ✅ | ✅ |
| Create vacancy | ❌ | ✅ | ✅ |
| Open vacancy editor | ✅ (read-only outside mutate actions) | ✅ | ✅ |
| Graph mutations (add/edit/delete/save) | ❌ | ✅ | ✅ |
| Suggestions decisions | ❌ | ✅ | ✅ |
| Tasks tab | ❌ | ✅ | ✅ |
| Ranking tab | ✅ | ✅ | ✅ |

## UX/State conventions

- Для async-состояний используется `AsyncState` (`loading/empty` паттерн).
- Для `403` используется явный `ForbiddenState` вместо generic ошибки.
- Уведомления централизованы через `notify(message, type, { duration })`.

## Smoke checklist

Ручной smoke regression: `FRONTEND_SMOKE_CHECKLIST.md`.
