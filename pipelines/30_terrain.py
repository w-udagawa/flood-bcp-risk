#!/usr/bin/env python3
"""地理院標高タイル（DEM5A txt）から、建物内DEM平均・周辺道路DEM平均・rel_elev・
簡易窪地判定（暫定指標）を算出する。

Requires:
  geopandas>=0.14, shapely>=2.0, pyproj>=3.6
  （DEM5A txt タイル自体の読み込みは標準ライブラリの csv のみで行う。
    dem5a はカンマ区切りテキストで、独自フォーマットのため rasterio の
    標準ドライバでは直接読めない想定）

本開発環境（GIS ライブラリ未導入・外部サイト到達不可）では実行できない。
ローカル環境で

    python3 pipelines/30_terrain.py \
        --buildings data/interim/meguro_2025_bldg.gpkg \
        --roads data/raw/context/ksj_n01/roads.shp \
        --dem-dir data/raw/dem/dem5a \
        --zoom 15 \
        --out data/interim/meguro_2025_terrain.csv

のように使う。DEM タイルは事前に `00_download.py` の bbox 指定実行で
`data/raw/dem/dem5a/{zoom}_{x}_{y}.txt` の形で取得しておくこと。

**未検証事項（V-03）**:
  対象区（目黒区・世田谷区）の DEM5A/DEM1A 整備状況、および dem5a タイルの
  最大ズームレベルは未確認。整備が無い区画は `ground_elev_m`/`road_elev_m`
  が None になる（features_schema.json 上は null 許容）。DEM1A（1mメッシュ）
  が使える区画では、`--dem-source dem1a` 相当のタイルパスに切り替えて
  精度を上げられるよう、タイル種別はテンプレート URL の差し替えのみで
  対応できる設計にしている（`pipelines/manifest.json` の
  gsi_dem5a_txt / gsi_dem5a_png 参照）。

**簡易窪地判定について（暫定実装、V-03 関連）**:
  タスクカードの指示に従い、Priority-Flood 等の本格的な depression-filling は
  使わず、「建物内平均 DEM が、建物重心を中心とする半径 50m 円内平均 DEM より
  0.3m 以上低い」ことを暫定の窪地指標（depression_flag）とする。
  本格実装（richdem の `rd.FillDepressions` や WhiteboxTools の
  `BreachDepressionsLeastCost`/`FillDepressions` 等）に差し替える際は、
  `compute_depression_flag()` のみを置き換えればよい設計とした
  （docs/research/C_地形基盤データ調査.md の「窪地・流入集中性の算出手法」節）。
"""

from __future__ import annotations

import argparse
import csv
import os

try:
    import geopandas as gpd  # type: ignore
    from shapely.geometry import Point  # type: ignore
except ImportError:  # pragma: no cover
    gpd = None
    Point = None

from lib import tiles

NODATA_MARKER = "e"  # GSI dem5a txt の欠測セル表記（想定、要現物確認）
DEPRESSION_THRESHOLD_M = 0.3
DEPRESSION_RADIUS_M = 50.0
ROAD_BUFFER_M = 30.0


def _require_geo():
    if gpd is None or Point is None:
        raise RuntimeError(
            "geopandas/shapely がインストールされていません。"
            " pip install -r pipelines/requirements-etl.txt を実行してください。"
        )


def parse_dem5a_txt(path: str) -> list[list[float | None]]:
    """DEM5A txt タイル（カンマ区切り、256x256 想定）を読み、グリッド値を返す。

    欠測セルは None。ファイル形式が想定と異なる場合に備え、数値変換できない
    セルは全て None として扱う（例外を送出しない）。
    """
    grid: list[list[float | None]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            parsed_row: list[float | None] = []
            for cell in row:
                cell = cell.strip()
                if not cell or cell.lower() == NODATA_MARKER:
                    parsed_row.append(None)
                    continue
                try:
                    parsed_row.append(float(cell))
                except ValueError:
                    parsed_row.append(None)
            if parsed_row:
                grid.append(parsed_row)
    return grid


class DemTileCache:
    """DEM タイルをディスクから読み込みメモリキャッシュする（zoom 固定）。"""

    def __init__(self, dem_dir: str, zoom: int):
        self.dem_dir = dem_dir
        self.zoom = zoom
        self._cache: dict[tuple[int, int], list[list[float | None]] | None] = {}

    def _load(self, x: int, y: int):
        key = (x, y)
        if key in self._cache:
            return self._cache[key]
        path = os.path.join(self.dem_dir, f"{self.zoom}_{x}_{y}.txt")
        if not os.path.exists(path):
            self._cache[key] = None
            return None
        grid = parse_dem5a_txt(path)
        self._cache[key] = grid
        return grid

    def elevation_at(self, lon: float, lat: float) -> float | None:
        tx, ty, col, row = tiles.lonlat_to_pixel(lon, lat, self.zoom)
        grid = self._load(tx, ty)
        if grid is None:
            return None
        if row >= len(grid) or col >= len(grid[row]):
            return None
        return grid[row][col]


def _sample_points_in_polygon(geom, spacing_m: float = 5.0):
    """ポリゴン内部を格子点でサンプリングし、(lon, lat) のリストを返す。

    geom は経度緯度（EPSG:4326）の shapely geometry を想定。
    spacing_m はおおよその間隔（緯度1度=約111km で近似変換、簡易実装）。
    """
    minx, miny, maxx, maxy = geom.bounds
    deg_spacing = spacing_m / 111_000.0
    if deg_spacing <= 0:
        deg_spacing = 0.00005
    points = []
    y = miny
    while y <= maxy:
        x = minx
        while x <= maxx:
            pt = Point(x, y)
            if geom.contains(pt) or geom.intersects(pt):
                points.append((x, y))
            x += deg_spacing
        y += deg_spacing
    if not points:
        # 極小ポリゴン対策: 重心のみを使う
        c = geom.centroid
        points = [(c.x, c.y)]
    return points


def mean_elevation_for_geometry(geom, dem_cache: DemTileCache, spacing_m: float = 5.0) -> float | None:
    points = _sample_points_in_polygon(geom, spacing_m=spacing_m)
    values = [v for v in (dem_cache.elevation_at(lon, lat) for lon, lat in points) if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def mean_elevation_for_road_buffer(building_geom, roads_gdf, dem_cache: DemTileCache, buffer_m: float = ROAD_BUFFER_M) -> float | None:
    """建物から buffer_m 以内の道路上の DEM 平均を求める。

    roads_gdf は経度緯度（EPSG:4326）を想定。距離計算の厳密さより実装単純さを
    優先した簡易実装（本格運用では DR-02 の平面直角座標系 EPSG:6677 に投影して
    バッファ計算するのが望ましい。TODO として明記）。
    """
    if roads_gdf is None or len(roads_gdf) == 0:
        return None
    buffer_deg = buffer_m / 111_000.0
    buffer_geom = building_geom.buffer(buffer_deg)
    nearby = roads_gdf[roads_gdf.intersects(buffer_geom)]
    if len(nearby) == 0:
        return None
    values = []
    for road_geom in nearby.geometry:
        clipped = road_geom.intersection(buffer_geom)
        if clipped.is_empty:
            continue
        length = clipped.length
        if length <= 0:
            # 点になった場合は端点のみサンプル
            pts = [(clipped.x, clipped.y)] if hasattr(clipped, "x") else []
        else:
            n_samples = max(2, int(length / (buffer_deg / 5)) if buffer_deg else 2)
            pts = []
            for i in range(n_samples):
                frac = i / (n_samples - 1) if n_samples > 1 else 0.0
                pt = clipped.interpolate(frac, normalized=True)
                pts.append((pt.x, pt.y))
        for lon, lat in pts:
            v = dem_cache.elevation_at(lon, lat)
            if v is not None:
                values.append(v)
    if not values:
        return None
    return sum(values) / len(values)


def compute_depression_flag(
    building_geom, dem_cache: DemTileCache, building_mean: float | None, spacing_m: float = 10.0
) -> bool | None:
    """暫定窪地指標: 建物内平均が半径50m平均より0.3m以上低いか。

    building_mean が None（DEM未整備等）の場合は None を返す（不明）。
    """
    if building_mean is None:
        return None
    centroid = building_geom.centroid
    radius_deg = DEPRESSION_RADIUS_M / 111_000.0
    circle = centroid.buffer(radius_deg)
    surrounding_mean = mean_elevation_for_geometry(circle, dem_cache, spacing_m=spacing_m)
    if surrounding_mean is None:
        return None
    return (surrounding_mean - building_mean) >= DEPRESSION_THRESHOLD_M


def process_buildings(buildings_gdf, roads_gdf, dem_cache: DemTileCache, building_id_field: str = "building_id") -> list[dict]:
    _require_geo()
    rows = []
    for _, feat in buildings_gdf.iterrows():
        geom = feat.geometry
        if geom is None or geom.is_empty:
            rows.append(
                {
                    "building_id": feat[building_id_field],
                    "ground_elev_m": None,
                    "road_elev_m": None,
                    "rel_elev_m": None,
                    "depression_flag": None,
                }
            )
            continue
        ground = mean_elevation_for_geometry(geom, dem_cache)
        road = mean_elevation_for_road_buffer(geom, roads_gdf, dem_cache)
        rel = (ground - road) if (ground is not None and road is not None) else None
        depression = compute_depression_flag(geom, dem_cache, ground)
        rows.append(
            {
                "building_id": feat[building_id_field],
                "ground_elev_m": ground,
                "road_elev_m": road,
                "rel_elev_m": rel,
                "depression_flag": depression,
            }
        )
    return rows


def write_terrain_csv(rows: list[dict], out_path: str) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    fieldnames = ["building_id", "ground_elev_m", "road_elev_m", "rel_elev_m", "depression_flag"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out_row = dict(row)
            if isinstance(out_row.get("depression_flag"), bool):
                out_row["depression_flag"] = "true" if out_row["depression_flag"] else "false"
            elif out_row.get("depression_flag") is None:
                out_row["depression_flag"] = ""
            for k in ("ground_elev_m", "road_elev_m", "rel_elev_m"):
                if out_row.get(k) is None:
                    out_row[k] = ""
            writer.writerow(out_row)
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buildings", required=True)
    parser.add_argument("--building-id-field", default="building_id")
    parser.add_argument("--roads", help="道路データ（N01 等）。未指定なら road_elev_m は全て null")
    parser.add_argument("--dem-dir", required=True, help="DEM5A txt タイルのディレクトリ（00_download.py の出力）")
    parser.add_argument("--zoom", type=int, default=15)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    _require_geo()
    buildings_gdf = gpd.read_file(args.buildings)
    if buildings_gdf.crs is not None and str(buildings_gdf.crs).upper() not in ("EPSG:4326",):
        buildings_gdf = buildings_gdf.to_crs("EPSG:4326")

    roads_gdf = None
    if args.roads:
        roads_gdf = gpd.read_file(args.roads)
        if roads_gdf.crs is not None and str(roads_gdf.crs).upper() not in ("EPSG:4326",):
            roads_gdf = roads_gdf.to_crs("EPSG:4326")

    dem_cache = DemTileCache(args.dem_dir, args.zoom)
    rows = process_buildings(buildings_gdf, roads_gdf, dem_cache, args.building_id_field)
    n = write_terrain_csv(rows, args.out)
    print(f"[OK] {n} 件の建物の地形特徴量を算出しました -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
