from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "API_MOCK_REFERENCE.md"
DST = ROOT / "kontest_mock_api" / "app" / "seed" / "endpoints.json"

SECTION_RE = re.compile(r"^##\s+(Integration|Judge|Courses)\s*$")
ENDPOINT_RE = re.compile(r"^###\s+GET\s+(.+)$")
VARIANT_RE = re.compile(r"^-\s+`([^`]+)`\s+\(`status\s+(\d+)`\)$")
CURL_RE = re.compile(r"^curl -sS '([^']+)' -H 'Authorization: Bearer ([^']+)'$")


def parse() -> list[dict]:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    items: list[dict] = []

    section = None
    endpoint = None
    i = 0
    while i < len(lines):
        line = lines[i]

        m = SECTION_RE.match(line)
        if m:
            section = m.group(1)
            i += 1
            continue

        m = ENDPOINT_RE.match(line)
        if m:
            endpoint = {"tag": section, "method": "GET", "path": m.group(1), "variants": []}
            items.append(endpoint)
            i += 1
            continue

        m = VARIANT_RE.match(line)
        if m and endpoint is not None:
            name, status = m.group(1), int(m.group(2))
            i += 1
            while i < len(lines) and lines[i] != "```bash":
                i += 1
            if i >= len(lines):
                break
            i += 1
            curl = lines[i] if i < len(lines) else ""
            cm = CURL_RE.match(curl)
            url = cm.group(1) if cm else ""
            token_hint = cm.group(2) if cm else ""

            while i < len(lines) and lines[i] != "```json":
                i += 1
            i += 1
            json_lines = []
            while i < len(lines) and lines[i] != "```":
                json_lines.append(lines[i])
                i += 1
            raw_json = "\n".join(json_lines).strip()
            payload = json.loads(raw_json) if raw_json else None

            endpoint["variants"].append(
                {
                    "name": name,
                    "status": status,
                    "url": url,
                    "token_hint": token_hint,
                    "response": payload,
                }
            )

        i += 1

    return items


def main() -> None:
    data = parse()
    DST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DST} with {len(data)} endpoints")


if __name__ == "__main__":
    main()
