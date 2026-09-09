#!/usr/bin/env python3
"""PLATEAU CityGML -> GeoPackage 変換ラッパ、および属性収録率レポート（V-01 対応）。

Requires:
  geopandas>=0.14, fiona>=1.9 （GeoPackage レイヤの読み込み）
  外部 CLI: PLATEAU GIS Converter
    https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter
    （`pipelines/manifest.json` の source_id=plateau_gis_converter。
      別途インストールし PATH に通しておくこと。pip では入らない）

本開発環境（外部サイト・バイナリ取得不可）では実行できない。ローカル環境で

    python3 pipelines/10_plateau_to_gpkg.py convert \
        --citygml data/raw/plateau/meguro_2025/udx/bldg \
        --out data/interim/meguro_2025_bldg.gpkg \
        --converter-bin plateau-gis-converter

    python3 pipelines/10_plateau_to_gpkg.py report \
        --gpkg data/interim/meguro_2025_bldg.gpkg \
        --out data/interim/meguro_2025_coverage_report.csv

のように 2 段階で使う（変換 / 収録率レポート）。

**未検証事項（V-01）**:
  PLATEAU GIS Converter が CityGML -> GeoPackage 変換時に、
  `gml:id` / `bldg:usage` / `storeysAboveGround` / `storeysBelowGround` /
  `measuredHeight` / `yearOfConstruction` / `uro:BuildingDetailAttribute`
  （totalFloorArea, buildingFootprintArea）/ 浸水リスク属性
  （河川・内水・高潮の depth・rank・duration、`uro:BuildingRiverFloodingRiskAttribute`
  等）を実際にどのようなフィールド名で GeoPackage に出力するかは、
  本開発環境では実データ・実ツールの出力を確認できていない
  （docs/research/A_建物データ調査.md も同旨を明記）。
  下記 `CANDIDATE_ATTRIBUTE_COLUMNS` は「想定される列名の候補」を
  複数列挙し、実データに存在する列を探索的に採用する設計としている。
  ローカルで一度変換した GeoPackage に対して

      python3 pipelines/10_plateau_to_gpkg.py inspect --gpkg <path>

  を実行し、実際の列名一覧を確認したうえで、本ファイルの
  `CANDIDATE_ATTRIBUTE_COLUMNS` を実列名に更新すること。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys

try:
    import geopandas as gpd  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None


# 抽出したい論理属性名 -> GeoPackage 上で取り得る列名の候補（優先順、先頭ほど有力）。
# 実データ未確認のため候補を広めに列挙している（V-01）。
CANDIDATE_ATTRIBUTE_COLUMNS: dict[str, list[str]] = {
    "gml_id": ["gml_id", "id", "gml:id"],
    "usage": ["usage", "bldg_usage", "bldg:usage"],
    "storeys_above": ["storeysAboveGround", "storeys_above_ground", "bldg_storeysAboveGround"],
    "storeys_below": ["storeysBelowGround", "storeys_below_ground", "bldg_storeysBelowGround"],
    "measured_height": ["measuredHeight", "measured_height", "bldg_measuredHeight"],
    "year_built": ["yearOfConstruction", "year_of_construction", "bldg_yearOfConstruction"],
    "total_floor_area_m2": [
        "totalFloorArea",
        "total_floor_area",
        "uro_totalFloorArea",
        "uro_BuildingDetailAttribute_totalFloorArea",
    ],
    "footprint_area_m2": [
        "buildingFootprintArea",
        "building_footprint_area",
        "uro_buildingFootprintArea",
        "uro_BuildingDetailAttribute_buildingFootprintArea",
    ],
    "river_depth": [
        "uro_BuildingRiverFloodingRiskAttribute_depth",
        "river_flooding_depth",
        "riverFloodingRiskAttribute_depth",
    ],
    "river_rank": [
        "uro_BuildingRiverFloodingRiskAttribute_rankOrg",
        "river_flooding_rank_org",
    ],
    "river_duration_h": [
        "uro_BuildingRiverFloodingRiskAttribute_duration",
        "river_flooding_duration",
    ],
    "inland_depth": [
        "uro_BuildingInlandFloodingRiskAttribute_depth",
        "inland_flooding_depth",
    ],
    "inland_rank": [
        "uro_BuildingInlandFloodingRiskAttribute_rankOrg",
        "inland_flooding_rank_org",
    ],
    "surge_depth": [
        "uro_BuildingHighTideRiskAttribute_depth",
        "high_tide_depth",
    ],
    "surge_rank": [
        "uro_BuildingHighTideRiskAttribute_rankOrg",
        "high_tide_rank_org",
    ],
}


def _require_geopandas():
    if gpd is None:
        raise RuntimeError(
            "geopandas がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def convert_citygml_to_gpkg(citygml_path: str, out_gpkg: str, converter_bin: str = "plateau-gis-converter") -> None:
    """PLATEAU GIS Converter CLI を呼び出して CityGML を GeoPackage に変換する。

    実際の CLI 引数（サブコマンド名・オプション名）は PLATEAU GIS Converter の
    バージョンに依存するため、ローカル環境で `plateau-gis-converter --help`
    を確認し、必要に応じて本関数のコマンドライン構築部分を調整すること。
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_gpkg)), exist_ok=True)
    cmd = [
        converter_bin,
        "fgb",  # 変換系サブコマンド名は要確認。gpkg 直接出力に対応する版もある。
        "--input",
        citygml_path,
        "--output",
        out_gpkg,
    ]
    print(f"[RUN] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def inspect_columns(gpkg_path: str, layer: str | None = None) -> list[str]:
    _require_geopandas()
    gdf = gpd.read_file(gpkg_path, layer=layer)
    return list(gdf.columns)


def _resolve_column(gdf, candidates: list[str]) -> str | None:
    lower_map = {str(c).lower(): c for c in gdf.columns}
    for cand in candidates:
        if cand in gdf.columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def coverage_report(gpkg_path: str, layer: str | None = None) -> list[dict]:
    """列ごとの非 null 率（収録率）を計算する（V-01 対応）。

    戻り値: [{"logical_name": ..., "resolved_column": ..., "non_null_count": ...,
              "total_count": ..., "non_null_rate": ...}, ...]
    """
    _require_geopandas()
    gdf = gpd.read_file(gpkg_path, layer=layer)
    total = len(gdf)
    rows = []
    for logical_name, candidates in CANDIDATE_ATTRIBUTE_COLUMNS.items():
        col = _resolve_column(gdf, candidates)
        if col is None:
            rows.append(
                {
                    "logical_name": logical_name,
                    "resolved_column": None,
                    "non_null_count": 0,
                    "total_count": total,
                    "non_null_rate": None,
                }
            )
            continue
        non_null = int(gdf[col].notna().sum())
        rows.append(
            {
                "logical_name": logical_name,
                "resolved_column": col,
                "non_null_count": non_null,
                "total_count": total,
                "non_null_rate": (non_null / total) if total else None,
            }
        )
    return rows


def write_coverage_report_csv(rows: list[dict], out_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fieldnames = ["logical_name", "resolved_column", "non_null_count", "total_count", "non_null_rate"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_convert = sub.add_parser("convert", help="CityGML -> GeoPackage 変換（PLATEAU GIS Converter 呼び出し）")
    p_convert.add_argument("--citygml", required=True)
    p_convert.add_argument("--out", required=True)
    p_convert.add_argument("--converter-bin", default="plateau-gis-converter")

    p_inspect = sub.add_parser("inspect", help="GeoPackage の列名一覧を表示（V-01 検証用）")
    p_inspect.add_argument("--gpkg", required=True)
    p_inspect.add_argument("--layer", default=None)

    p_report = sub.add_parser("report", help="属性ごとの非null率（収録率）レポートを出力")
    p_report.add_argument("--gpkg", required=True)
    p_report.add_argument("--layer", default=None)
    p_report.add_argument("--out", required=True, help="レポート出力先 CSV パス")

    args = parser.parse_args(argv)

    if args.command == "convert":
        convert_citygml_to_gpkg(args.citygml, args.out, args.converter_bin)
        return 0

    if args.command == "inspect":
        cols = inspect_columns(args.gpkg, args.layer)
        print(json.dumps(cols, ensure_ascii=False, indent=2))
        return 0

    if args.command == "report":
        rows = coverage_report(args.gpkg, args.layer)
        write_coverage_report_csv(rows, args.out)
        for row in rows:
            rate = row["non_null_rate"]
            rate_str = f"{rate:.1%}" if rate is not None else "N/A（列未検出）"
            print(f"{row['logical_name']:24s} -> {row['resolved_column'] or '(not found)':45s} {rate_str}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
