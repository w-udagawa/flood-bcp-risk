"""地理院標高タイル（dem5a 等、Web メルカトル XYZ タイル）の座標計算。

標準ライブラリ（math）のみに依存する純 Python モジュール。
地理院タイルは Google 系スリッピーマップと同じ XYZ 規約
（`https://maps.gsi.go.jp/development/siyou.html`）を使うため、
一般的な Web メルカトルタイル座標計算をそのまま適用できる。

`pipelines/30_terrain.py` から、建物・道路の緯度経度に対応する
DEM タイル（z/x/y）とタイル内ピクセル位置を求めるために使う。
"""

from __future__ import annotations

import math

TILE_SIZE = 256


def lonlat_to_tile_xy(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    """経度緯度・ズームレベルから、タイル座標 (x, y) を返す（標準スリッピーマップ規約）。

    lat は Web メルカトルの有効範囲（およそ ±85.0511 度）にクリップする。
    """
    lat_rad = math.radians(_clip_lat(lat))
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
    )
    x = max(0, min(int(n) - 1, x))
    y = max(0, min(int(n) - 1, y))
    return x, y


def lonlat_to_pixel(lon: float, lat: float, zoom: int, tile_size: int = TILE_SIZE) -> tuple[int, int, int, int]:
    """経度緯度・ズームレベルから (tile_x, tile_y, pixel_col, pixel_row) を返す。

    pixel_col/pixel_row はタイル内のピクセル位置（左上原点、0..tile_size-1）。
    DEM5A の 1 タイルは 256x256 の標高値グリッドに対応するため、
    ``tile_size=256`` が既定。
    """
    lat_rad = math.radians(_clip_lat(lat))
    n = 2.0 ** zoom
    world_x = (lon + 180.0) / 360.0 * n * tile_size
    world_y = (
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
        * tile_size
    )
    max_pixel = n * tile_size
    world_x = max(0.0, min(max_pixel - 1e-9, world_x))
    world_y = max(0.0, min(max_pixel - 1e-9, world_y))

    tile_x = int(world_x // tile_size)
    tile_y = int(world_y // tile_size)
    pixel_col = int(world_x - tile_x * tile_size)
    pixel_row = int(world_y - tile_y * tile_size)
    return tile_x, tile_y, pixel_col, pixel_row


def tile_url(template: str, zoom: int, x: int, y: int) -> str:
    """`{z}/{x}/{y}` プレースホルダを含む URL テンプレートを埋める。

    例: template="https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt"
    """
    return template.format(z=zoom, x=x, y=y)


def tile_bounds_lonlat(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    """タイル座標 (x, y, z) から、そのタイルの経度緯度範囲を返す。

    戻り値: (west_lon, north_lat, east_lon, south_lat)
    """
    n = 2.0 ** zoom
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _mercator_y_to_lat(y / n)
    south = _mercator_y_to_lat((y + 1) / n)
    return west, north, east, south


def _mercator_y_to_lat(y_frac: float) -> float:
    n = math.pi * (1 - 2 * y_frac)
    return math.degrees(math.atan(math.sinh(n)))


def _clip_lat(lat: float) -> float:
    max_lat = 85.05112878
    return max(-max_lat, min(max_lat, lat))
