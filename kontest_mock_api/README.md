# kontest_mock_api

Lightweight FastAPI mock for Kontest endpoints (`Integration`, `Judge`, `Courses`) based on `API_MOCK_REFERENCE.md` snapshots.

## Run (uv)

```bash
cd kontest_mock_api
uv sync
uv run uvicorn app.main:app --reload --port 8181
```

## Tokens

- Integration: `integration-token-diplom`
- Admin: `admin-mock-token`

## Behavior

- Only GET endpoints from the snapshot are implemented.
- `Integration` endpoints require integration token.
- `Judge` and `Courses` endpoints require admin token.
- Path/query combinations are resolved against captured variants from `API_MOCK_REFERENCE.md`.
- `X-Mock-Variant` response header shows which snapshot variant was used.

## Refresh seeds

```bash
uv run python app/extract_seed.py
```
