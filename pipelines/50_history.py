#!/usr/bin/env python3
"""浸水実績ポリゴン（手動作成 GeoJSON 想定）と建物の 30m バッファ結合。

Requires:
  geopandas>=0.14, shapely>=2.0, pyproj>=3.6

本開発環境では実行できない。ローカル環境で

    python3 pipelines/50_history.py \
        --buildings data/interim/meguro_2025_bldg.gpkg \
        --history data/manual/flood_history_meguro.geojson \
        --year-field event_year \
        --out data/interim/meguro_2025_history.csv

のように使う。

**入力データについて（V-04 関連）**:
  `--history` に渡す GeoJSON は、`pipelines/manifest.json` の
  `tokyo_flood_history_system`（ダウンロード可否未検証）が使えない場合、
  `meguro_hazard_map_pdf` / `setagaya_hazard_map_pdf`（区の浸水実績図 PDF）を
  人手でジオリファレンスし、QGIS 等で手動ポリゴン化して作成することを想定する
  （docs/02_要件定義書.md 13章のリスク対策、docs/tasks/TASK-003_ETL骨格.md）。
  本スクリプトはその手動ポリゴンを入力として受け取るだけで、
  自動ダウンロード・自動ジオリファレンスは行わない。

  GeoJSON の属性スキーマは以下を想定（未確定、ローカルでの手動作成時に
  この形式に合わせるか、`--year-field`/`--depth-field` で読み替える）:
    - event_year（int, 例: 2025）または任意の年フィールド
    - depth_m（float, 任意）
"""

from __future__ import annotations

import argparse
import csv
import os

try:
    import geopandas as gpd  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None

PLANAR_CRS = "EPSG:6677"
HISTORY_BUFFER_M = 30.0


def _require_geo():
    if gpd is None:
        raise RuntimeError(
            "geopandas がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def join_flood_history(
    buildings_gdf,
    history_gdf,
    year_field: str | None,
    building_id_field: str = "building_id",
    buffer_m: float = HISTORY_BUFFER_M,
) -> list[dict]:
    """建物ごとに、建物本体または buffer_m 以内に浸水実績ポリゴンがあるか判定する。"""
    _require_geo()
    buildings_p = buildings_gdf.to_crs(PLANAR_CRS)
    history_p = history_gdf.to_crs(PLANAR_CRS)

    rows = []
    for _, feat in buildings_p.iterrows():
        geom = feat.geometry
        building_id = feat[building_id_field]
        if geom is None or geom.is_empty:
            rows.append({"building_id": building_id, "flood_history_flag": None, "flood_history_years": None})
            continue

        search_area = geom.buffer(buffer_m)
        hits = history_p[history_p.intersects(search_area)]
        if len(hits) == 0:
            rows.append({"building_id": building_id, "flood_history_flag": False, "flood_history_years": None})
            continue

        years: list[str] = []
        if year_field and year_field in hits.columns:
            for v in hits[year_field].tolist():
                if v is None:
                    continue
                years.append(str(v))
        years_str = ",".join(sorted(set(years))) if years else None

        rows.append({"building_id": building_id, "flood_history_flag": True, "flood_history_years": years_str})
    return rows


def write_history_csv(rows: list[dict], out_path: str) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fieldnames = ["building_id", "flood_history_flag", "flood_history_years"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flag = row.get("flood_history_flag")
            writer.writerow(
                {
                    "building_id": row["building_id"],
                    "flood_history_flag": "" if flag is None else ("true" if flag else "false"),
                    "flood_history_years": row.get("flood_history_years") or "",
                }
            )
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buildings", required=True)
    parser.add_argument("--building-id-field", default="building_id")
    parser.add_argument("--history", required=True, help="浸水実績ポリゴン GeoJSON（手動作成想定）")
    parser.add_argument("--year-field", default="event_year")
    parser.add_argument("--buffer-m", type=float, default=HISTORY_BUFFER_M)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    _require_geo()
    buildings_gdf = gpd.read_file(args.buildings)
    history_gdf = gpd.read_file(args.history)

    rows = join_flood_history(
        buildings_gdf, history_gdf, args.year_field, args.building_id_field, args.buffer_m
    )
    n = write_history_csv(rows, args.out)
    print(f"[OK] {n} 件の建物の浸水実績を判定しました -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
