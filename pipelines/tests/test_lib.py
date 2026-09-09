"""pipelines/lib/ の単体テスト（標準ライブラリのみ、GIS 依存なし）。

実行:
    python3 -m unittest discover -s pipelines/tests -v

TASK-003 受入基準の対象: usage_map の境界、depth_classes の写像、
tiles の座標計算。加えて csv_io / schema_check の基本動作も確認する。
"""

from __future__ import annotations

import math
import os
import sys
import unittest

# `python3 -m unittest discover -s pipelines/tests` で実行した場合、
# sys.path には pipelines/tests が積まれ pipelines/lib は見えないため、
# pipelines/ を明示的に sys.path に追加してから lib.* を import する。
_PIPELINES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PIPELINES_DIR not in sys.path:
    sys.path.insert(0, _PIPELINES_DIR)

from lib import csv_io, depth_classes, schema_check, tiles, usage_map  # noqa: E402


class TestUsageMap(unittest.TestCase):
    def test_known_codes_map_to_base_class(self):
        self.assertEqual(usage_map.base_usage_class_from_code("401"), "office")
        self.assertEqual(usage_map.base_usage_class_from_code("402"), "commercial")
        self.assertEqual(usage_map.base_usage_class_from_code("411"), "residential")
        self.assertEqual(usage_map.base_usage_class_from_code("421"), "public_critical")
        self.assertEqual(usage_map.base_usage_class_from_code("462"), "other")

    def test_unknown_or_none_code_returns_none(self):
        self.assertIsNone(usage_map.base_usage_class_from_code(None))
        self.assertIsNone(usage_map.base_usage_class_from_code(""))
        self.assertIsNone(usage_map.base_usage_class_from_code("999"))

    def test_commercial_large_boundary(self):
        # 延床 10,000 未満 -> commercial
        self.assertEqual(
            usage_map.determine_usage_class("402", total_floor_area_m2=9_999.999),
            "commercial",
        )
        # 延床 = 10,000（境界値、以上なので large） -> commercial_large
        self.assertEqual(
            usage_map.determine_usage_class("402", total_floor_area_m2=10_000.0),
            "commercial_large",
        )
        # 延床 10,000 超 -> commercial_large
        self.assertEqual(
            usage_map.determine_usage_class("402", total_floor_area_m2=15_000.0),
            "commercial_large",
        )
        # 延床不明（None） -> commercial のまま
        self.assertEqual(usage_map.determine_usage_class("402"), "commercial")

    def test_residential_large_boundary_by_floor_area(self):
        self.assertEqual(
            usage_map.determine_usage_class("412", total_floor_area_m2=9_999.9),
            "residential",
        )
        self.assertEqual(
            usage_map.determine_usage_class("412", total_floor_area_m2=10_000.0),
            "residential_large",
        )

    def test_residential_large_boundary_by_storeys(self):
        self.assertEqual(
            usage_map.determine_usage_class("412", storeys_above=9),
            "residential",
        )
        self.assertEqual(
            usage_map.determine_usage_class("412", storeys_above=10),
            "residential_large",
        )
        self.assertEqual(
            usage_map.determine_usage_class("412", storeys_above=15),
            "residential_large",
        )

    def test_hint_overrides_take_priority(self):
        # usage_code 上は office(401) だが、病院フラグが立っていれば hospital
        self.assertEqual(
            usage_map.determine_usage_class("401", hospital_flag=True),
            "hospital",
        )
        # 運輸倉庫施設(431)でも station_hint があれば station
        self.assertEqual(
            usage_map.determine_usage_class("431", station_hint=True),
            "station",
        )
        # hospital_flag は station_hint より優先される
        self.assertEqual(
            usage_map.determine_usage_class("431", station_hint=True, hospital_flag=True),
            "hospital",
        )

    def test_unknown_code_without_hints_is_other(self):
        self.assertEqual(usage_map.determine_usage_class("999"), "other")
        self.assertEqual(usage_map.determine_usage_class(None), "other")

    def test_all_table_values_are_valid_usage_classes(self):
        for code, cls in usage_map.USAGE_CODE_TABLE.items():
            with self.subTest(code=code):
                self.assertIn(cls, usage_map.VALID_USAGE_CLASSES)


class TestDepthClasses(unittest.TestCase):
    def test_load_tables_contains_expected_sources(self):
        tables = depth_classes.load_tables()
        self.assertIn("tokyo_inundation_map", tables)
        self.assertIn("ksj_a31", tables)
        self.assertIn("ksj_a51", tables)
        self.assertIn("ksj_a49", tables)

    def test_tokyo_inundation_map_class_ranges(self):
        rng = depth_classes.depth_range_for_code("tokyo_inundation_map", "1")
        self.assertEqual(rng, (0.0, 0.1))
        rng_top = depth_classes.depth_range_for_code("tokyo_inundation_map", "6")
        self.assertEqual(rng_top, (5.0, None))

    def test_ksj_a31_class_ranges(self):
        self.assertEqual(depth_classes.depth_range_for_code("ksj_a31", "1"), (0.0, 0.5))
        self.assertEqual(depth_classes.depth_range_for_code("ksj_a31", "2"), (0.5, 3.0))
        self.assertEqual(depth_classes.depth_range_for_code("ksj_a31", "5"), (10.0, 20.0))

    def test_unknown_source_or_code_returns_none_tuple(self):
        self.assertEqual(depth_classes.depth_range_for_code("no_such_source", "1"), (None, None))
        self.assertEqual(depth_classes.depth_range_for_code("ksj_a31", "no_such_code"), (None, None))

    def test_tables_marked_unverified(self):
        tables = depth_classes.load_tables()
        for source_id in ("tokyo_inundation_map", "ksj_a31", "ksj_a51", "ksj_a49"):
            with self.subTest(source_id=source_id):
                self.assertFalse(tables[source_id].verified)

    def test_combine_max_range_picks_highest_lower_bound(self):
        ranges = [(0.1, 0.5), (0.5, 1.0), None, (0.0, 0.1)]
        self.assertEqual(depth_classes.combine_max_range(ranges), (0.5, 1.0))

    def test_combine_max_range_all_none_returns_none_tuple(self):
        self.assertEqual(depth_classes.combine_max_range([None, None]), (None, None))

    def test_combine_max_range_single_value(self):
        self.assertEqual(depth_classes.combine_max_range([(1.0, 2.0)]), (1.0, 2.0))


class TestTiles(unittest.TestCase):
    def test_lonlat_to_tile_xy_tokyo_station_zoom10(self):
        # 東京駅付近（東経139.767, 北緯35.681）、zoom=10 での標準的なタイル座標
        x, y = tiles.lonlat_to_tile_xy(139.767, 35.681, 10)
        self.assertEqual((x, y), (909, 403))

    def test_lonlat_to_tile_xy_origin(self):
        # (0, 0) 付近は世界地図の中心
        x, y = tiles.lonlat_to_tile_xy(0.0, 0.0, 1)
        self.assertEqual((x, y), (1, 1))

    def test_lonlat_to_pixel_consistent_with_tile_xy(self):
        lon, lat, zoom = 139.767, 35.681, 10
        tx, ty = tiles.lonlat_to_tile_xy(lon, lat, zoom)
        px_tx, px_ty, col, row = tiles.lonlat_to_pixel(lon, lat, zoom)
        self.assertEqual((tx, ty), (px_tx, px_ty))
        self.assertTrue(0 <= col < tiles.TILE_SIZE)
        self.assertTrue(0 <= row < tiles.TILE_SIZE)

    def test_lonlat_to_pixel_zoom18_within_dem5a_tile(self):
        # DEM5A は 1タイル=256x256、zoom=15 相当の詳細度で配信される
        # (地理院タイル仕様: dem5a は z=15 が基本)。座標が有効範囲に収まることを確認。
        tx, ty, col, row = tiles.lonlat_to_pixel(139.6681, 35.6006, 15)  # 自由が丘付近
        self.assertGreaterEqual(tx, 0)
        self.assertGreaterEqual(ty, 0)
        self.assertTrue(0 <= col < 256)
        self.assertTrue(0 <= row < 256)

    def test_tile_url_formats_placeholders(self):
        url = tiles.tile_url(
            "https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt", 15, 29112, 12930
        )
        self.assertEqual(url, "https://cyberjapandata.gsi.go.jp/xyz/dem5a/15/29112/12930.txt")

    def test_tile_bounds_roundtrip_contains_center(self):
        zoom = 12
        x, y = tiles.lonlat_to_tile_xy(139.767, 35.681, zoom)
        west, north, east, south = tiles.tile_bounds_lonlat(x, y, zoom)
        self.assertLess(west, east)
        self.assertLess(south, north)
        self.assertTrue(west <= 139.767 <= east)
        self.assertTrue(south <= 35.681 <= north)

    def test_clip_lat_does_not_raise_at_poles(self):
        # 極域に近い値でも math domain error を起こさないこと
        x, y = tiles.lonlat_to_tile_xy(0.0, 89.9, 5)
        self.assertTrue(0 <= x < 2 ** 5)
        self.assertTrue(0 <= y < 2 ** 5)


class TestCsvIo(unittest.TestCase):
    def test_format_csv_value_null_and_bool(self):
        self.assertEqual(csv_io.format_csv_value(None), "")
        self.assertEqual(csv_io.format_csv_value(True), "true")
        self.assertEqual(csv_io.format_csv_value(False), "false")
        self.assertEqual(csv_io.format_csv_value(3.5), "3.5")
        self.assertEqual(csv_io.format_csv_value("bldg_1"), "bldg_1")

    def test_row_to_csv_row_fills_missing_as_blank(self):
        row = {"building_id": "b1", "height_m": None}
        out = csv_io.row_to_csv_row(row, ["building_id", "height_m", "ward_code"])
        self.assertEqual(out, {"building_id": "b1", "height_m": "", "ward_code": ""})

    def test_write_and_read_back_csv(self):
        import csv
        import tempfile

        rows = [
            {"building_id": "b1", "flood_history_flag": True, "height_m": 12.3},
            {"building_id": "b2", "flood_history_flag": False, "height_m": None},
        ]
        fieldnames = ["building_id", "flood_history_flag", "height_m"]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "features.csv")
            n = csv_io.write_features_csv(rows, fieldnames, path)
            self.assertEqual(n, 2)
            with open(path, newline="", encoding="utf-8") as f:
                read_rows = list(csv.DictReader(f))
        self.assertEqual(read_rows[0]["flood_history_flag"], "true")
        self.assertEqual(read_rows[1]["flood_history_flag"], "false")
        self.assertEqual(read_rows[1]["height_m"], "")

    def test_write_and_read_back_jsonl(self):
        import json
        import tempfile

        rows = [{"building_id": "b1", "height_m": None, "flood_history_flag": True}]
        fieldnames = ["building_id", "height_m", "flood_history_flag"]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "features.jsonl")
            n = csv_io.write_features_jsonl(rows, fieldnames, path)
            self.assertEqual(n, 1)
            with open(path, encoding="utf-8") as f:
                line = f.readline()
        obj = json.loads(line)
        self.assertIsNone(obj["height_m"])
        self.assertIs(obj["flood_history_flag"], True)


class TestSchemaCheck(unittest.TestCase):
    def _schema_path(self):
        return os.path.join(
            os.path.dirname(_PIPELINES_DIR), "config", "features_schema.json"
        )

    def test_load_real_schema_and_validate_minimal_row(self):
        schema = schema_check.load_schema(self._schema_path())
        row = {"building_id": "bldg_1"}
        errors = schema_check.validate_row(row, schema)
        self.assertEqual(errors, [])

    def test_missing_required_field_is_error(self):
        schema = schema_check.load_schema(self._schema_path())
        errors = schema_check.validate_row({"ward_code": "13110"}, schema)
        self.assertTrue(any("building_id" in e for e in errors))

    def test_wrong_type_is_error(self):
        schema = schema_check.load_schema(self._schema_path())
        errors = schema_check.validate_row(
            {"building_id": "bldg_1", "storeys_above": "3"}, schema
        )
        self.assertTrue(any("storeys_above" in e for e in errors))

    def test_additional_property_rejected(self):
        schema = schema_check.load_schema(self._schema_path())
        errors = schema_check.validate_row(
            {"building_id": "bldg_1", "not_in_schema": 1}, schema
        )
        self.assertTrue(any("not_in_schema" in e for e in errors))

    def test_nullable_field_accepts_none(self):
        schema = schema_check.load_schema(self._schema_path())
        errors = schema_check.validate_row(
            {"building_id": "bldg_1", "height_m": None}, schema
        )
        self.assertEqual(errors, [])

    def test_boolean_field_rejects_int(self):
        schema = schema_check.load_schema(self._schema_path())
        errors = schema_check.validate_row(
            {"building_id": "bldg_1", "depression_flag": 1}, schema
        )
        self.assertTrue(any("depression_flag" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
