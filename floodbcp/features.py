"""建物特徴量（features）の読み込みとスキーマ検証。

docs/03_スコアリング仕様.md 第1章 / config/features_schema.json に対応する。
スキーマは JSON から読むだけで、フィールド一覧をここに二重定義しない。
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Iterable, Iterator

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent
DEFAULT_SCHEMA_PATH = _REPO_ROOT / "config" / "features_schema.json"


class SchemaError(ValueError):
    """features_schema.json に反する入力（未知フィールド・必須欠落・型不正）。"""


def _json_type_to_kind(json_types: Any) -> str:
    """JSON Schema の "type" （文字列 or ["string","null"] 等）から、
    null を除いた主要種別（string/integer/number/boolean）を返す。
    """
    types = json_types if isinstance(json_types, list) else [json_types]
    for t in types:
        if t != "null":
            return t
    return "null"


def load_schema(schema_path: Path | str = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _field_kinds(schema: dict[str, Any]) -> dict[str, str]:
    return {name: _json_type_to_kind(prop["type"]) for name, prop in schema["properties"].items()}


# Feature データクラスのフィールドは features_schema.json の properties と一致させる。
# (dataclass 自体は静的な型ヒントのために定義するが、実行時の検証・未知フィールド検出は
#  load_schema() が返すスキーマに対して行う。)
@dataclass
class Feature:
    building_id: str
    ward_code: str | None = None
    name: str | None = None
    usage_code: str | None = None
    usage_class: str | None = None
    storeys_above: int | None = None
    storeys_below: int | None = None
    height_m: float | None = None
    year_built: int | None = None
    total_floor_area_m2: float | None = None
    footprint_area_m2: float | None = None
    inland_depth_min_m: float | None = None
    inland_depth_max_m: float | None = None
    river_depth_min_m: float | None = None
    river_depth_max_m: float | None = None
    river_duration_h: float | None = None
    surge_depth_min_m: float | None = None
    surge_depth_max_m: float | None = None
    flood_history_flag: bool | None = None
    flood_history_years: str | None = None
    ground_elev_m: float | None = None
    road_elev_m: float | None = None
    rel_elev_m: float | None = None
    depression_flag: bool | None = None
    landform_class: str | None = None
    station_ridership: int | None = None
    is_station_facility: bool | None = None
    hospital_flag: bool | None = None
    welfare_flag: bool | None = None
    public_flag: bool | None = None
    alt_facility_dist_m: float | None = None
    data_versions: str | None = None
    hazard_source_year: int | None = None

    def get(self, field_name: str) -> Any:
        return getattr(self, field_name)

    def as_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


_FEATURE_FIELD_NAMES = {f.name for f in fields(Feature)}


def _convert_csv_scalar(raw: str, kind: str, *, row_no: int, field_name: str) -> Any:
    raw = raw.strip()
    if raw == "":
        return None
    if kind == "string":
        return raw
    if kind == "boolean":
        lowered = raw.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        raise SchemaError(
            f"row {row_no}: field {field_name!r} は boolean ですが true/false ではありません: {raw!r}"
        )
    if kind == "integer":
        try:
            return int(raw)
        except ValueError as exc:
            raise SchemaError(
                f"row {row_no}: field {field_name!r} は integer に変換できません: {raw!r}"
            ) from exc
    if kind == "number":
        try:
            return float(raw)
        except ValueError as exc:
            raise SchemaError(
                f"row {row_no}: field {field_name!r} は number に変換できません: {raw!r}"
            ) from exc
    raise SchemaError(f"unsupported schema kind {kind!r} for field {field_name!r}")


def _validate_and_build(
    raw_row: dict[str, Any], field_kinds: dict[str, str], required: Iterable[str], *, row_no: int
) -> Feature:
    unknown = set(raw_row) - set(field_kinds)
    if unknown:
        raise SchemaError(f"row {row_no}: 未知のフィールド: {sorted(unknown)}")

    for req in required:
        if raw_row.get(req) in (None, ""):
            raise SchemaError(f"row {row_no}: 必須フィールド {req!r} が欠落しています")

    kwargs = {name: raw_row.get(name) for name in _FEATURE_FIELD_NAMES if name in raw_row}
    return Feature(**kwargs)


def load_features_csv(
    path: Path | str, schema_path: Path | str = DEFAULT_SCHEMA_PATH
) -> list[Feature]:
    schema = load_schema(schema_path)
    field_kinds = _field_kinds(schema)
    required = schema.get("required", [])

    features: list[Feature] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_no, row in enumerate(reader, start=2):  # 1 行目はヘッダ
            if None in row:
                raise SchemaError(f"row {row_no}: 列数がヘッダと一致しません")
            raw_row: dict[str, Any] = {}
            for col, raw_value in row.items():
                if col not in field_kinds:
                    # 未知列はここでは変換できないので生文字列のまま渡し、
                    # _validate_and_build で未知フィールドとしてエラーにする。
                    raw_row[col] = raw_value
                    continue
                raw_row[col] = _convert_csv_scalar(
                    raw_value or "", field_kinds[col], row_no=row_no, field_name=col
                )
            features.append(_validate_and_build(raw_row, field_kinds, required, row_no=row_no))
    return features


def load_features_jsonl(
    path: Path | str, schema_path: Path | str = DEFAULT_SCHEMA_PATH
) -> list[Feature]:
    schema = load_schema(schema_path)
    field_kinds = _field_kinds(schema)
    required = schema.get("required", [])

    features: list[Feature] = []
    with open(path, encoding="utf-8") as f:
        for row_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise SchemaError(f"line {row_no}: JSON オブジェクトではありません")
            features.append(_validate_and_build(obj, field_kinds, required, row_no=row_no))
    return features


def load_features(
    path: Path | str, schema_path: Path | str = DEFAULT_SCHEMA_PATH
) -> list[Feature]:
    """拡張子から CSV / JSON Lines を判定して読み込む。"""
    p = Path(path)
    if p.suffix.lower() in (".jsonl", ".ndjson", ".json"):
        return load_features_jsonl(p, schema_path)
    return load_features_csv(p, schema_path)
