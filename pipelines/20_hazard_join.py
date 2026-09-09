#!/usr/bin/env python3
"""建物ポリゴンとハザードポリゴン（内水・洪水・高潮・地形分類）の空間結合。

Requires:
  geopandas>=0.14, shapely>=2.0, pyproj>=3.6

本開発環境（GIS ライブラリ未導入・外部サイト到達不可）では実行できない。
ローカル環境で

    python3 pipelines/20_hazard_join.py \
        --buildings data/interim/meguro_2025_bldg.gpkg \
        --hazard-source tokyo_inundation_map \
        --hazard-file data/raw/hazard/tokyo_inundation_map/inundation.shp \
        --class-field <実属性名> \
        --hazard-type inland \
        --out data/interim/meguro_2025_hazard_inland.csv

のように、ハザード種別（inland/river/surge）ごとに 1 回ずつ実行し、
`60_export_features.py` で他工程の出力とマージする想定。

建物ごとに交差する階級の最大（下限・上限）を取る、という結合方針は
docs/tasks/TASK-003_ETL骨格.md および docs/03_スコアリング仕様.md 3-1 に従う
（各ソースの階級**下限**を代表値とし、複数ポリゴンが交差する場合は
下限が最大のものを採用 = `pipelines/lib/depth_classes.combine_max_range`）。

**未検証事項（V-02 / V-05 / V-06）**:
  階級コード -> (下限, 上限) の写像表は `pipelines/config/depth_class_tables.json`
  に外出ししているが、実データの属性値では検証していない
  （`pipelines/lib/depth_classes.py` の docstring 参照）。
  `--class-field` に渡す実属性名も、実際に取得した Shapefile/GeoPackage を
  QGIS 等で開いて確認する必要がある。
  地形分類（landform_class、`--landform-file` オプション）の実タイル URL・
  属性コード値も未検証（V-06）。
"""

from __future__ import annotations

import argparse
import csv
import os

try:
    import geopandas as gpd  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None

from lib.depth_classes import combine_max_range, load_tables

HAZARD_TYPE_TO_FIELDS = {
    "inland": ("inland_depth_min_m", "inland_depth_max_m"),
    "river": ("river_depth_min_m", "river_depth_max_m"),
    "surge": ("surge_depth_min_m", "surge_depth_max_m"),
}


def _require_geopandas():
    if gpd is None:
        raise RuntimeError(
            "geopandas がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def join_buildings_with_hazard(
    buildings_gdf,
    hazard_gdf,
    class_field: str,
    source_id: str,
    building_id_field: str = "building_id",
):
    """建物ごとに、交差するハザードポリゴンの階級から代表 (min_m, max_m) を求める。

    戻り値: {building_id: (min_m, max_m)}。交差なしの建物は含まれない
    （呼び出し側で None 埋めする）。
    """
    _require_geopandas()
    tables = load_tables()
    table = tables.get(source_id)
    if table is None:
        raise ValueError(f"depth_class_tables.json に source_id='{source_id}' が定義されていません。")

    joined = gpd.sjoin(
        buildings_gdf[[building_id_field, "geometry"]],
        hazard_gdf[[class_field, "geometry"]],
        predicate="intersects",
        how="inner",
    )

    result: dict[str, tuple] = {}
    grouped = joined.groupby(building_id_field)[class_field]
    for building_id, codes in grouped:
        ranges = [table.range_for(code) for code in codes]
        result[building_id] = combine_max_range(ranges)
    return result


def write_hazard_csv(result: dict, hazard_type: str, out_path: str) -> int:
    min_field, max_field = HAZARD_TYPE_TO_FIELDS[hazard_type]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    count = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["building_id", min_field, max_field])
        writer.writeheader()
        for building_id, (lo, hi) in result.items():
            writer.writerow(
                {
                    "building_id": building_id,
                    min_field: "" if lo is None else lo,
                    max_field: "" if hi is None else hi,
                }
            )
            count += 1
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buildings", required=True, help="建物ポリゴン GeoPackage/GeoJSON")
    parser.add_argument("--building-id-field", default="building_id")
    parser.add_argument("--hazard-source", required=True, help="depth_class_tables.json の source_id")
    parser.add_argument("--hazard-file", required=True, help="ハザードポリゴン Shapefile/GeoPackage/GeoJSON")
    parser.add_argument("--class-field", required=True, help="ハザードファイル中の階級コード列名（要現物確認、V-02）")
    parser.add_argument("--hazard-type", required=True, choices=list(HAZARD_TYPE_TO_FIELDS.keys()))
    parser.add_argument("--out", required=True, help="出力 CSV パス（building_id, *_min_m, *_max_m）")
    args = parser.parse_args(argv)

    _require_geopandas()
    buildings_gdf = gpd.read_file(args.buildings)
    hazard_gdf = gpd.read_file(args.hazard_file)

    if buildings_gdf.crs != hazard_gdf.crs:
        hazard_gdf = hazard_gdf.to_crs(buildings_gdf.crs)

    result = join_buildings_with_hazard(
        buildings_gdf, hazard_gdf, args.class_field, args.hazard_source, args.building_id_field
    )
    n = write_hazard_csv(result, args.hazard_type, args.out)
    print(f"[OK] {n} 件の建物にハザード階級を付与しました -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
