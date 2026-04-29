from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException, status


@dataclass(frozen=True)
class Variant:
    name: str
    status_code: int
    query: dict[str, list[str]]
    response: Any
    seed_path: str


@dataclass(frozen=True)
class EndpointSeed:
    tag: str
    method: str
    template_path: str
    concrete_path: str
    path_params: dict[str, str]
    query_param_names: list[str]
    variants: list[Variant]


class DataStore:
    def __init__(self, seed_path: Path) -> None:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        self._by_template: dict[str, EndpointSeed] = {}
        for item in raw:
            variants: list[Variant] = []
            concrete_path = ""
            for v in item["variants"]:
                parsed = urlsplit(v["url"])
                if not concrete_path:
                    concrete_path = parsed.path
                query = {k: sorted(vals) for k, vals in parse_qs(parsed.query, keep_blank_values=True).items()}
                variants.append(
                    Variant(
                        name=v["name"],
                        status_code=int(v["status"]),
                        query=query,
                        response=v["response"],
                        seed_path=parsed.path,
                    )
                )

            template = item["path"]
            self._by_template[template] = EndpointSeed(
                tag=item["tag"],
                method=item["method"],
                template_path=template,
                concrete_path=concrete_path,
                path_params=self._extract_path_params(template, concrete_path),
                query_param_names=self._extract_query_param_names(variants),
                variants=variants,
            )

    @staticmethod
    def _extract_path_params(template: str, concrete: str) -> dict[str, str]:
        tp = template.strip("/").split("/")
        cp = concrete.strip("/").split("/")
        out: dict[str, str] = {}
        for t, c in zip(tp, cp):
            if t.startswith("{") and t.endswith("}"):
                out[t[1:-1]] = c
        return out

    @staticmethod
    def _extract_query_param_names(variants: list[Variant]) -> list[str]:
        keys: set[str] = set()
        for variant in variants:
            keys.update(variant.query.keys())
        return sorted(keys)

    def list_by_tag(self, tag: str) -> list[EndpointSeed]:
        return [s for s in self._by_template.values() if s.tag == tag]

    def resolve(self, template_path: str, path_params: dict[str, str], query_params: dict[str, list[str]]) -> tuple[int, Any, str]:
        seed = self._by_template.get(template_path)
        if seed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not seeded")

        for k, expected in seed.path_params.items():
            if path_params.get(k) != expected:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

        normalized_query = {k: sorted(v) for k, v in query_params.items()}

        exact = self._find_variant(seed.variants, normalized_query)
        if exact is not None:
            return exact.status_code, exact.response, exact.name

        default = next((v for v in seed.variants if v.name == "default"), seed.variants[0])
        return default.status_code, default.response, default.name

    @staticmethod
    def _find_variant(variants: list[Variant], q: dict[str, list[str]]) -> Variant | None:
        for variant in variants:
            if variant.query == q:
                return variant
        return None
