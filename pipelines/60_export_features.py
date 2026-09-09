#!/usr/bin/env python3
"""10〜50 の中間成果物を建物 ID で結合し、features.csv / features.jsonl を出力する。

Requires:
  geopandas>=0.14  （建物ポリゴンの基本属性 GeoPackage 読み込みのみ。
                      それ以外のマージ・書き出し・スキーマ検証は標準ライブラリのみで行う）

本開発環境では建物ポリゴン GeoPackage の読み込み部分（geopandas）は動かないが、
それ以外（CSV マージ・usage_class 決定・スキーマ検証・CSV/JSONL 書き出し）は
`pipelines/lib/` の純 Python 実装であり、`pipelines/tests/test_lib.py` で
標準ライブラリのみでテスト済み。

ローカル環境での実行例:

    python3 pipelines/60_export_features.py \
        --buildings-gpkg data/interim/meguro_2025_bldg.gpkg \
        --ward-code 13110 \
        --merge-csv data/interim/meguro_2025_hazard_inland.csv \
        --merge-csv data/interim/meguro_2025_hazard_river.csv \
        --merge-csv data/interim/meguro_2025_terrain.csv \
        --merge-csv data/interim/meguro_2025_context.csv \
        --merge-csv data/interim/meguro_2025_history.csv \
        --data-version plateau_meguro_2025+ksj_a31_2025+... \
        --hazard-source-year 2024 \
        --out-csv data/out/features.csv \
        --out-jsonl data/out/features.jsonl \
        --report-out data/out/schema_validation_report.json

`--merge-csv` は building_id 列を主キーとする CSV を任意個数受け取り、
`config/features_schema.json` に存在する列だけを features に取り込む
（20_hazard_join.py / 30_terrain.py / 40_context.py / 50_history.py の
それぞれの出力をそのまま渡せる）。

出力後、`config/features_schema.json` に対して標準ライブラリのみで
型チェックを行い（`pipelines/lib/schema_check.py`）、違反があれば
`--report-out` にレポートを書き出し、終了コード 1 を返す。
"""

from __future__ import annotations

import argparse
import csv
import json
import os

try:
    import geopandas as gpd  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None

from lib import csv_io, schema_check, usage_map

DEFAULT_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "config", "features_schema.json"
)

# 建物ポリゴン GeoPackage 上の基礎属性列名候補。
# 10_plateau_to_gpkg.py の CANDIDATE_ATTRIBUTE_COLUMNS と同じ考え方（V-01 未検証）。
# モジュール名が数字始まりで import 不可のため、要点のみここに複製している。
BASE_ATTRIBUTE_CANDIDATES: dict[str, list[str]] = {
    "building_id": ["gml_id", "id", "building_id"],
    "usage_code": ["usage", "bldg_usage", "usage_code"],
    "storeys_above": ["storeysAboveGround", "storeys_above_ground", "storeys_above"],
    "storeys_below": ["storeysBelowGround", "storeys_below_ground", "storeys_below"],
    "height_m": ["measuredHeight", "measured_height", "height_m"],
    "year_built": ["yearOfConstruction", "year_of_construction", "year_built"],
    "total_floor_area_m2": ["totalFloorArea", "total_floor_area", "total_floor_area_m2"],
    "footprint_area_m2": ["buildingFootprintArea", "building_footprint_area", "footprint_area_m2"],
    "name": ["name", "bldg_name"],
}


def _require_geopandas():
    if gpd is None:
        raise RuntimeError(
            "geopandas がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def _resolve_column(columns, candidates: list[str]) -> str | None:
    lower_map = {str(c).lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def load_base_rows(gpkg_path: str, ward_code: str | None, layer: str | None = None) -> dict[str, dict]:
    """建物ポリゴン GeoPackage から features の基礎列だけを取り出す。

    戻り値: {building_id: {建物基礎属性の dict}}
    """
    _require_geopandas()
    gdf = gpd.read_file(gpkg_path, layer=layer)
    resolved = {k: _resolve_column(gdf.columns, v) for k, v in BASE_ATTRIBUTE_CANDIDATES.items()}

    id_col = resolved["building_id"]
    if id_col is None:
        raise RuntimeError(
            "建物 ID 列（gml_id 等）が GeoPackage に見つかりません。"
            " 10_plateau_to_gpkg.py inspect で列名を確認してください。"
        )

    rows: dict[str, dict] = {}
    for _, feat in gdf.iterrows():
        building_id = str(feat[id_col])
        row = {"building_id": building_id, "ward_code": ward_code}
        for logical, col in resolved.items():
            if logical in ("building_id",):
                continue
            row[logical] = feat[col] if col is not None else None
        rows[building_id] = row
    return rows


def coerce_csv_value(raw: str, prop_schema: dict):
    """CSV から読んだ文字列を features_schema の型に合わせて Python 値へ変換する。

    空文字は None（欠損）とする（CSV の null 表現規約）。
    """
    if raw is None or raw == "":
        return None
    types = prop_schema.get("type")
    types = [types] if isinstance(types, str) else list(types or [])

    if "boolean" in types and raw.strip().lower() in ("true", "false", "1", "0"):
        return raw.strip().lower() in ("true", "1")
    if "integer" in types:
        try:
            return int(float(raw))
        except ValueError:
            pass
    if "number" in types:
        try:
            return float(raw)
        except ValueError:
            pass
    return raw


def merge_csv_into_rows(rows: dict[str, dict], csv_path: str, schema_properties: dict) -> None:
    """CSV（building_id をキーに持つ）の内容を rows（building_id -> dict）にマージする。

    schema_properties に存在する列のみ取り込む（additionalProperties: false に整合）。
    building_id が rows に無い場合は新規行として追加する
    （例: 建物ポリゴン側に無いが結合データにだけ現れるケースの取りこぼし防止）。
    """
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for csv_row in reader:
            building_id = csv_row.get("building_id")
            if not building_id:
                continue
            target = rows.setdefault(building_id, {"building_id": building_id})
            for key, raw_value in csv_row.items():
                if key == "building_id":
                    continue
                if key not in schema_properties:
                    continue
                target[key] = coerce_csv_value(raw_value, schema_properties[key])


def apply_usage_class(rows: dict[str, dict]) -> None:
    for row in rows.values():
        row["usage_class"] = usage_map.determine_usage_class(
            row.get("usage_code"),
            total_floor_area_m2=row.get("total_floor_area_m2"),
            storeys_above=row.get("storeys_above"),
            hospital_flag=bool(row.get("hospital_flag")),
            welfare_flag=bool(row.get("welfare_flag")),
            station_hint=bool(row.get("is_station_facility")),
            public_hint=bool(row.get("public_flag")),
        )


def apply_constant_fields(rows: dict[str, dict], data_version: str | None, hazard_source_year: int | None) -> None:
    for row in rows.values():
        if data_version is not None:
            row["data_versions"] = data_version
        if hazard_source_year is not None:
            row["hazard_source_year"] = hazard_source_year


def validate_rows_against_schema(rows: dict[str, dict], schema: dict) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for building_id, row in rows.items():
        errs = schema_check.validate_row(row, schema)
        if errs:
            errors[building_id] = errs
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buildings-gpkg", required=True)
    parser.add_argument("--layer", default=None)
    parser.add_argument("--ward-code", default=None, help="5桁市区町村コード（例: 目黒区=13110, 世田谷区=13112）")
    parser.add_argument("--merge-csv", action="append", default=[], help="building_id をキーに持つマージ元 CSV（複数指定可）")
    parser.add_argument("--data-version", default=None)
    parser.add_argument("--hazard-source-year", type=int, default=None)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--report-out", default=None, help="スキーマ検証エラーの詳細を書き出す JSON パス")
    args = parser.parse_args(argv)

    schema = schema_check.load_schema(args.schema)
    schema_properties = schema.get("properties", {})
    fieldnames = list(schema_properties.keys())

    rows = load_base_rows(args.buildings_gpkg, args.ward_code, args.layer)

    for csv_path in args.merge_csv:
        merge_csv_into_rows(rows, csv_path, schema_properties)

    apply_usage_class(rows)
    apply_constant_fields(rows, args.data_version, args.hazard_source_year)

    errors = validate_rows_against_schema(rows, schema)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_jsonl)) or ".", exist_ok=True)
    n_csv = csv_io.write_features_csv(rows.values(), fieldnames, args.out_csv)
    n_jsonl = csv_io.write_features_jsonl(rows.values(), fieldnames, args.out_jsonl)
    print(f"[OK] {n_csv} 件を書き出しました -> {args.out_csv}")
    print(f"[OK] {n_jsonl} 件を書き出しました -> {args.out_jsonl}")

    if errors:
        print(f"[WARN] スキーマ検証エラー: {len(errors)} / {len(rows)} 件の建物でエラーがありました。")
        if args.report_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.report_out)) or ".", exist_ok=True)
            with open(args.report_out, "w", encoding="utf-8") as f:
                json.dump(errors, f, ensure_ascii=False, indent=2)
            print(f"[WARN] 詳細レポート -> {args.report_out}")
        else:
            for building_id, errs in list(errors.items())[:20]:
                print(f"  - {building_id}: {errs}")
        return 1

    print("[OK] スキーマ検証: 全件エラーなし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
