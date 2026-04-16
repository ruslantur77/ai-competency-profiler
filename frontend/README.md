# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## API base URL

- Default API base URL: `'/api/v1'`.
- Local dev uses Vite proxy (`/api` -> `http://localhost:1000`).
- In Docker/Nginx runtime set `FRONTEND_API_BASE_URL` (for example `https://api.example.com/api/v1`).

## API layer conventions

- Base axios instance and auth refresh interceptor: `src/api/base.js`.
- Domain modules:
  - `src/api/auth.js`
  - `src/api/vacancies.js`
  - `src/api/tasks.js`
  - `src/api/ranking.js`
  - `src/api/suggestions.js`
- Response normalization helpers: `src/api/adapters.js`.
- Centralized user-facing error mapping: `src/api/errors.js`.
- Compatibility barrel: `src/api/client.js` (re-export only, no business logic).
- Legacy unavailable endpoints are isolated in `src/api/legacy-stubs.js` and are not part of production flow.

## Role visibility matrix

- Backend source of truth for current user: `GET /auth/me`.
- Frontend keeps role in app-level state and updates it on login and token refresh events.

| Feature | HR | EXPERT | ADMIN |
|---------|----|--------|-------|
| Vacancies list/read | ✅ | ✅ | ✅ |
| Create vacancy | ❌ | ✅ | ✅ |
| Open vacancy editor | ✅ (read-only) | ✅ | ✅ |
| Graph mutations (add/edit/delete/save) | ❌ | ✅ | ✅ |
| Suggestions decisions | ❌ | ✅ | ✅ |
| Tasks tab | ❌ | ✅ | ✅ |
| Ranking tab | ✅ | ✅ | ✅ |
