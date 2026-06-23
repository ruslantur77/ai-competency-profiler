from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from .auth import authenticate, ensure_access
from .data_store import DataStore

app = FastAPI(title="Kontest Mock API", version="0.1.0")
store = DataStore(Path(__file__).parent / "seed" / "endpoints.json")


def _parameter_schema(name: str) -> dict[str, Any]:
    if name == "course_ids":
        return {"type": "array", "items": {"type": "integer"}}
    if name.endswith("_id") or name == "user_id":
        return {"type": "integer"}
    if name.startswith("include_"):
        return {"type": "boolean"}
    if name.startswith("updated_"):
        return {"type": "string", "format": "date-time"}
    return {"type": "string"}


def _openapi_parameters(template: str, query_names: list[str]) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    path_names = re.findall(r"{([^{}]+)}", template)
    for name in path_names:
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": _parameter_schema(name),
            }
        )
    for name in query_names:
        params.append(
            {
                "name": name,
                "in": "query",
                "required": name == "course_ids",
                "schema": _parameter_schema(name),
            }
        )
    return params


def _operation_id(path: str) -> str:
    return "get_" + re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")


def _summary(path: str) -> str:
    return f"Mock GET {path}"


def _make_handler(template: str, tag: str):
    async def handler(request: Request) -> JSONResponse:
        principal = authenticate(request)
        ensure_access(principal.role, tag)

        query = {k: request.query_params.getlist(k) for k in request.query_params.keys()}
        path_params = {k: str(v) for k, v in request.path_params.items()}
        code, payload, variant = store.resolve(template, path_params, query)

        headers = {
            "X-Mock-Variant": variant,
            "X-Mock-Role": principal.role,
        }
        return JSONResponse(status_code=code, content=payload, headers=headers)

    return handler


def _register_tag_routes(tag: str) -> None:
    endpoints = store.list_by_tag(tag)

    for endpoint in endpoints:
        template = endpoint.template_path
        handler = _make_handler(template, tag)
        app.add_api_route(
            template,
            handler,
            methods=["GET"],
            tags=[tag],
            operation_id=_operation_id(template),
            summary=_summary(template),
            responses={
                200: {"description": "Successful Response"},
                401: {"description": "Unauthorized"},
                403: {"description": "Forbidden"},
                404: {"description": "Not Found"},
                422: {"description": "Validation Error"},
            },
            openapi_extra={
                "parameters": _openapi_parameters(template, endpoint.query_param_names),
                "security": [{"HTTPBearer": []}],
            },
        )


for _tag in ("Integration", "Judge", "Courses"):
    _register_tag_routes(_tag)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["HTTPBearer"] = {"type": "http", "scheme": "bearer"}
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health", tags=["System"])
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "kontest-mock-api"}
