from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request, status

INTEGRATION_TOKEN = "integration-token-diplom"
ADMIN_TOKEN = "admin-mock-token"


@dataclass(frozen=True)
class Principal:
    role: str
    token: str


def _extract_bearer(request: Request) -> str:
    value = request.headers.get("Authorization")
    if not value or not value.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = value[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return token


def authenticate(request: Request) -> Principal:
    token = _extract_bearer(request)
    if token == INTEGRATION_TOKEN:
        return Principal(role="integration", token=token)
    if token == ADMIN_TOKEN:
        return Principal(role="admin", token=token)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def ensure_access(role: str, tag: str) -> None:
    if tag == "Integration" and role != "integration":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if tag in {"Judge", "Courses"} and role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
