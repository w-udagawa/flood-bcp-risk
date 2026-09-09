#!/usr/bin/env python3
"""S12（駅別乗降客数）・N02（鉄道）・P04（医療機関）・P14（福祉施設）・
P02/P05（公共施設）から、影響度関連の特徴量を算出する。

Requires:
  geopandas>=0.14, shapely>=2.0, pyproj>=3.6

本開発環境では実行できない。ローカル環境で

    python3 pipelines/40_context.py \
        --buildings data/interim/meguro_2025_bldg.gpkg \
        --stations data/raw/context/ksj_n02/stations.shp \
        --ridership data/raw/context/ksj_s12/ridership.shp \
        --hospitals data/raw/context/ksj_p04/hospitals.shp \
        --welfare data/raw/context/ksj_p14/welfare.shp \
        --public data/raw/context/ksj_p02_p05/public.shp \
        --out data/interim/meguro_2025_context.csv

のように使う（P02/P05 は `pipelines/manifest.json` で url:null, manual:true。
ローカルで nlftp.mlit.go.jp の datalist から該当製品を特定すること）。

出力列: building_id, station_ridership, is_station_facility, hospital_flag,
        welfare_flag, public_flag, alt_facility_dist_m

**設計上の注意（Fable が判断すべき未決事項として README にも転記）**:
  - alt_facility_dist_m（同用途の代替施設距離）は
    docs/03_スコアリング仕様.md の記載どおり「商業・医療のみ算出」とし、
    それ以外の usage_class では None を出力する。
    「同用途」の判定粒度（commercial 同士か、commercial_large も含めるか等）
    は未規定のため、本実装では `usage_class` の完全一致を「同用途」とした。
  - is_station_facility は「建物ポリゴンが駅点（N02）から
    `STATION_PROXIMITY_M` m 以内にある」ことを条件とする暫定ロジック。
    駅ビル・地下鉄駅施設の的確な判定には usage_code との組み合わせ確認が
    必要（V-01 の usage 収録率次第）。
"""

from __future__ import annotations

import argparse
import csv
import os

try:
    import geopandas as gpd  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None

PLANAR_CRS = "EPSG:6677"  # JGD2011 平面直角座標系第9系（docs/02_要件定義書.md DR-02）
STATION_PROXIMITY_M = 300.0  # 最寄り駅とみなす距離（03_スコアリング仕様.md 「300m以内」）
STATION_FACILITY_PROXIMITY_M = 50.0  # 駅施設自体とみなす距離（暫定）
FLAG_PROXIMITY_M = 20.0  # hospital_flag 等の POI が建物と同一とみなす距離（暫定、ジオコード誤差許容）
ALT_FACILITY_USAGE_CLASSES = {"commercial", "commercial_large", "hospital"}


def _require_geo():
    if gpd is None:
        raise RuntimeError(
            "geopandas がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def _to_planar(gdf):
    if gdf is None:
        return None
    return gdf.to_crs(PLANAR_CRS)


def nearest_ridership(building_geom, ridership_gdf, ridership_field: str, max_dist_m: float = STATION_PROXIMITY_M):
    if ridership_gdf is None or len(ridership_gdf) == 0:
        return None
    dists = ridership_gdf.geometry.distance(building_geom)
    idx = dists.idxmin()
    if dists.loc[idx] > max_dist_m:
        return None
    value = ridership_gdf.loc[idx, ridership_field]
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_station_facility(building_geom, stations_gdf, max_dist_m: float = STATION_FACILITY_PROXIMITY_M) -> bool:
    if stations_gdf is None or len(stations_gdf) == 0:
        return False
    dists = stations_gdf.geometry.distance(building_geom)
    return bool((dists <= max_dist_m).any())


def flag_within_distance(building_geom, poi_gdf, max_dist_m: float = FLAG_PROXIMITY_M) -> bool:
    if poi_gdf is None or len(poi_gdf) == 0:
        return False
    dists = poi_gdf.geometry.distance(building_geom)
    return bool((dists <= max_dist_m).any())


def alt_facility_distance(building_geom, same_usage_gdf, self_index=None) -> float | None:
    """同用途の代替施設までの最短距離（自分自身を除く）。"""
    if same_usage_gdf is None or len(same_usage_gdf) == 0:
        return None
    candidates = same_usage_gdf
    if self_index is not None and self_index in candidates.index:
        candidates = candidates.drop(index=self_index)
    if len(candidates) == 0:
        return None
    dists = candidates.geometry.distance(building_geom)
    if len(dists) == 0:
        return None
    return float(dists.min())


def process_buildings(
    buildings_gdf,
    stations_gdf=None,
    ridership_gdf=None,
    ridership_field: str = "S12_001",
    hospitals_gdf=None,
    welfare_gdf=None,
    public_gdf=None,
    building_id_field: str = "building_id",
    usage_class_field: str = "usage_class",
) -> list[dict]:
    _require_geo()

    buildings_p = _to_planar(buildings_gdf)
    stations_p = _to_planar(stations_gdf)
    ridership_p = _to_planar(ridership_gdf)
    hospitals_p = _to_planar(hospitals_gdf)
    welfare_p = _to_planar(welfare_gdf)
    public_p = _to_planar(public_gdf)

    # alt_facility_dist_m 用: 建物レイヤ自身の重心（商業・医療系施設の代表点）
    same_usage_source = None
    if usage_class_field in buildings_p.columns:
        same_usage_source = buildings_p.copy()
        same_usage_source["geometry"] = same_usage_source.geometry.centroid

    rows = []
    for idx, feat in buildings_p.iterrows():
        geom = feat.geometry
        building_id = feat[building_id_field]
        usage_class = feat[usage_class_field] if usage_class_field in feat else None

        if geom is None or geom.is_empty:
            rows.append(
                {
                    "building_id": building_id,
                    "station_ridership": None,
                    "is_station_facility": None,
                    "hospital_flag": None,
                    "welfare_flag": None,
                    "public_flag": None,
                    "alt_facility_dist_m": None,
                }
            )
            continue

        centroid = geom.centroid

        ridership = nearest_ridership(centroid, ridership_p, ridership_field)
        station_flag = is_station_facility(geom, stations_p)
        hospital_flag = flag_within_distance(geom, hospitals_p)
        welfare_flag = flag_within_distance(geom, welfare_p)
        public_flag = flag_within_distance(geom, public_p)

        alt_dist = None
        if usage_class in ALT_FACILITY_USAGE_CLASSES and same_usage_source is not None:
            same_usage_subset = same_usage_source[same_usage_source[usage_class_field] == usage_class]
            alt_dist = alt_facility_distance(centroid, same_usage_subset, self_index=idx)

        rows.append(
            {
                "building_id": building_id,
                "station_ridership": ridership,
                "is_station_facility": station_flag,
                "hospital_flag": hospital_flag,
                "welfare_flag": welfare_flag,
                "public_flag": public_flag,
                "alt_facility_dist_m": alt_dist,
            }
        )
    return rows


def write_context_csv(rows: list[dict], out_path: str) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fieldnames = [
        "building_id",
        "station_ridership",
        "is_station_facility",
        "hospital_flag",
        "welfare_flag",
        "public_flag",
        "alt_facility_dist_m",
    ]
    bool_fields = {"is_station_facility", "hospital_flag", "welfare_flag", "public_flag"}
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out_row = {}
            for k in fieldnames:
                v = row.get(k)
                if v is None:
                    out_row[k] = ""
                elif k in bool_fields:
                    out_row[k] = "true" if v else "false"
                else:
                    out_row[k] = v
            writer.writerow(out_row)
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buildings", required=True, help="usage_class 列を含む建物ポリゴン（10/20 工程後の中間成果物）")
    parser.add_argument("--building-id-field", default="building_id")
    parser.add_argument("--usage-class-field", default="usage_class")
    parser.add_argument("--stations", help="N02 鉄道（駅点）")
    parser.add_argument("--ridership", help="S12 駅別乗降客数")
    parser.add_argument("--ridership-field", default="S12_001", help="乗降客数の属性列名（要現物確認）")
    parser.add_argument("--hospitals", help="P04 医療機関")
    parser.add_argument("--welfare", help="P14 福祉施設")
    parser.add_argument("--public", help="P02/P05 公共施設（url 未確定、ローカルで個別取得）")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    _require_geo()
    buildings_gdf = gpd.read_file(args.buildings)
    stations_gdf = gpd.read_file(args.stations) if args.stations else None
    ridership_gdf = gpd.read_file(args.ridership) if args.ridership else None
    hospitals_gdf = gpd.read_file(args.hospitals) if args.hospitals else None
    welfare_gdf = gpd.read_file(args.welfare) if args.welfare else None
    public_gdf = gpd.read_file(args.public) if args.public else None

    rows = process_buildings(
        buildings_gdf,
        stations_gdf=stations_gdf,
        ridership_gdf=ridership_gdf,
        ridership_field=args.ridership_field,
        hospitals_gdf=hospitals_gdf,
        welfare_gdf=welfare_gdf,
        public_gdf=public_gdf,
        building_id_field=args.building_id_field,
        usage_class_field=args.usage_class_field,
    )
    n = write_context_csv(rows, args.out)
    print(f"[OK] {n} 件の建物のコンテキスト特徴量を算出しました -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
