"""`config/features_schema.json` に対する簡易スキーマ検証（標準ライブラリのみ）。

jsonschema 等の外部ライブラリは使わず、本スキーマが実際に使う範囲
（フラットな object・"type" が文字列またはリスト・required・
additionalProperties: false）だけをサポートする軽量な自作バリデータ。

`pipelines/60_export_features.py` から、features 1行ごとの検証に使う。
"""

from __future__ import annotations

import json
from typing import Any

_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}


def load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _type_list(prop_schema: dict) -> list[str]:
    t = prop_schema.get("type")
    if t is None:
        return []
    if isinstance(t, str):
        return [t]
    return list(t)


def validate_value(value: Any, prop_schema: dict) -> bool:
    """1つの値が、1つのプロパティスキーマ（"type" のみ考慮）に適合するか判定する。"""
    types = _type_list(prop_schema)
    if not types:
        return True
    for t in types:
        checker = _TYPE_CHECKERS.get(t)
        if checker is not None and checker(value):
            return True
    return False


def validate_row(row: dict, schema: dict) -> list[str]:
    """1行分（dict）を features_schema に照らして検証し、エラー文言のリストを返す。

    エラーが無ければ空リスト。row は Python ネイティブ型（None/bool/int/
    float/str）を想定する（CSV から読み直す場合は事前に型変換すること）。
    """
    errors: list[str] = []
    properties: dict = schema.get("properties", {})
    required: list[str] = schema.get("required", [])
    additional_ok = schema.get("additionalProperties", True)

    for req_key in required:
        if req_key not in row or row.get(req_key) is None:
            errors.append(f"required field missing or null: {req_key}")

    if not additional_ok:
        for key in row.keys():
            if key not in properties:
                errors.append(f"additional property not allowed: {key}")

    for key, prop_schema in properties.items():
        if key not in row:
            continue
        value = row[key]
        if not validate_value(value, prop_schema):
            expected = prop_schema.get("type")
            errors.append(
                f"field '{key}' has invalid type: expected {expected}, got {type(value).__name__} ({value!r})"
            )

    return errors


def validate_rows(rows, schema: dict) -> dict[int, list[str]]:
    """複数行を検証し、{行インデックス: エラーリスト} を返す（エラーがある行のみ）。"""
    result: dict[int, list[str]] = {}
    for i, row in enumerate(rows):
        errs = validate_row(row, schema)
        if errs:
            result[i] = errs
    return result
