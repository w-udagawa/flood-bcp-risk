"""テスト用の共通ヘルパー（unittest discover には拾われない）。"""
from __future__ import annotations

import dataclasses
from typing import Any

from floodbcp.features import Feature

FIXED_COMPUTED_AT = "2026-09-09T00:00:00Z"  # as_of_year = 2026

# 補正・欠損の影響を受けない「中立」なベース特徴量。
# 個々のテストは必要なフィールドだけ上書きする。
_BASE_KWARGS: dict[str, Any] = dict(
    building_id="bldg_test",
    ward_code="13100",
    name="テスト建物",
    usage_code="000",
    usage_class="office",
    storeys_above=3,
    storeys_below=0,
    height_m=15.0,
    year_built=2000,
    total_floor_area_m2=2000.0,
    footprint_area_m2=800.0,
    inland_depth_min_m=0.0,
    inland_depth_max_m=0.0,
    river_depth_min_m=0.0,
    river_depth_max_m=0.0,
    river_duration_h=None,
    surge_depth_min_m=None,
    surge_depth_max_m=None,
    flood_history_flag=False,
    flood_history_years=None,
    ground_elev_m=10.0,
    road_elev_m=10.0,
    rel_elev_m=0.0,
    depression_flag=False,
    landform_class=None,
    station_ridership=None,
    is_station_facility=False,
    hospital_flag=False,
    welfare_flag=False,
    public_flag=False,
    alt_facility_dist_m=None,
    data_versions="test_v0",
    hazard_source_year=2024,
)


def make_feature(**overrides: Any) -> Feature:
    kwargs = {**_BASE_KWARGS, **overrides}
    return Feature(**kwargs)
