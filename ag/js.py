from __future__ import annotations

import json
import ast
from typing import Any


def _find_json_span(s: str) -> tuple[int, int] | None:
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return None


def load_obj(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[-1].strip()
    span = _find_json_span(text)
    if span is None:
        raise ValueError("no_json_object_found")
    a, b = span
    chunk = text[a:b]
    try:
        obj = json.loads(chunk)
    except json.JSONDecodeError:
        obj = ast.literal_eval(chunk)
    if not isinstance(obj, dict):
        raise ValueError("json_root_not_object")
    for k in obj.keys():
        if not isinstance(k, str):
            raise ValueError("json_keys_not_str")
    return obj
