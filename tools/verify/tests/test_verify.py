"""tools/verify/ の単体テスト（標準ライブラリのみ、ネットワーク不使用）。

実行:
    python3 -m unittest discover -s tools/verify/tests -v

対象（docs/tasks/TASK-006_M1検証ツールキット.md 受入基準）:
  - dbf_inspect: バイナリ生成した小さな .dbf をパースして検証
  - gpkg_fill_rate: sqlite3 で gpkg_contents + ダミー建物テーブルを作って検証
  - tile_probe: URL 列挙のみ検証（ネットワーク不使用、--fetch は呼ばない）
  - depth_class_check: 既知コード・未知コードの検出を検証
"""

from __future__ import annotations

import io
import os
import sqlite3
import struct
import sys
import tempfile
import unittest
import zipfile

# `python3 -m unittest discover -s tools/verify/tests` 実行時、sys.path には
# tools/verify/tests が積まれ tools/verify/ 直下のモジュールは見えないため、
# 明示的に追加する（pipelines/tests/test_lib.py と同じ方式）。
_VERIFY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _VERIFY_DIR not in sys.path:
    sys.path.insert(0, _VERIFY_DIR)

import dbf_inspect  # noqa: E402
import depth_class_check  # noqa: E402
import gpkg_fill_rate  # noqa: E402
import tile_probe  # noqa: E402


# ---------------------------------------------------------------------------
# dBase III .dbf バイナリを組み立てるテスト用ヘルパー
# ---------------------------------------------------------------------------

def _build_dbf(fields: list[tuple[str, str, int, int]], records: list[list[str]]) -> bytes:
    """(name, type, length, decimal) のリストと、値（文字列）の行リストから
    dBase III 形式の .dbf バイナリを組み立てる。値は左詰めでフィールド長に
    パディングする（右側をスペース埋め）。空文字列を渡すとその列は
    「全角スペース埋め＝非null判定されない値」になる。
    """
    record_len = 1 + sum(f[2] for f in fields)
    header_len = 32 + 32 * len(fields) + 1

    header = bytearray(32)
    header[0] = 0x03  # dBase III, no memo
    header[1:4] = bytes([24, 1, 1])  # 更新日（適当な値）
    struct.pack_into("<I", header, 4, len(records))
    struct.pack_into("<H", header, 8, header_len)
    struct.pack_into("<H", header, 10, record_len)

    field_descs = bytearray()
    for name, type_code, length, decimal in fields:
        desc = bytearray(32)
        name_bytes = name.encode("ascii")[:10]
        desc[0 : len(name_bytes)] = name_bytes
        desc[11] = ord(type_code)
        desc[16] = length
        desc[17] = decimal
        field_descs += desc

    body = bytearray()
    for row in records:
        body += b" "  # deletion flag: 有効レコード
        for value, (name, type_code, length, decimal) in zip(row, fields):
            raw = value.encode("cp932")
            if len(raw) > length:
                raw = raw[:length]
            raw = raw + b" " * (length - len(raw))
            body += raw

    return bytes(header) + bytes(field_descs) + b"\x0d" + bytes(body) + b"\x1a"


class TestDbfInspect(unittest.TestCase):
    FIELDS = [
        ("NAME", "C", 10, 0),
        ("CLASSCODE", "C", 2, 0),
        ("DEPTH", "N", 5, 1),
        ("ISWET", "L", 1, 0),
    ]

    RECORDS = [
        ["Building A", "1", "0.3", "T"],
        ["Building B", "2", "1.2", "F"],
        ["Building C", "1", "", " "],  # DEPTH・ISWET が null
        ["", "3", "5.0", "T"],  # NAME が null
    ]

    def setUp(self):
        self.dbf_bytes = _build_dbf(self.FIELDS, self.RECORDS)

    def test_parse_dbf_field_list_and_record_count(self):
        result = dbf_inspect.parse_dbf(io.BytesIO(self.dbf_bytes), encoding="cp932", top_n=20)
        self.assertEqual(result["actual_record_count"], 4)
        self.assertEqual(result["declared_record_count"], 4)
        field_names = [f["name"] for f in result["fields"]]
        self.assertEqual(field_names, ["NAME", "CLASSCODE", "DEPTH", "ISWET"])

        by_name = {f["name"]: f for f in result["fields"]}
        self.assertEqual(by_name["NAME"]["type"], "C")
        self.assertEqual(by_name["DEPTH"]["type"], "N")
        self.assertEqual(by_name["DEPTH"]["decimal_count"], 1)
        self.assertEqual(by_name["ISWET"]["type"], "L")

    def test_non_null_rate(self):
        result = dbf_inspect.parse_dbf(io.BytesIO(self.dbf_bytes), encoding="cp932", top_n=20)
        by_name = {f["name"]: f for f in result["fields"]}

        # NAME: 4件中3件が非空文字（1件は空文字列）
        self.assertEqual(by_name["NAME"]["non_null_count"], 3)
        self.assertAlmostEqual(by_name["NAME"]["non_null_rate"], 0.75)

        # DEPTH: 4件中3件が非null（1件は空欄）
        self.assertEqual(by_name["DEPTH"]["non_null_count"], 3)

        # ISWET: 4件中3件が T/F、1件がスペース（未設定＝null扱い）
        self.assertEqual(by_name["ISWET"]["non_null_count"], 3)

    def test_top_values_and_unique_count(self):
        result = dbf_inspect.parse_dbf(io.BytesIO(self.dbf_bytes), encoding="cp932", top_n=20)
        by_name = {f["name"]: f for f in result["fields"]}
        classcode = by_name["CLASSCODE"]
        self.assertEqual(classcode["unique_count"], 3)
        values = {v["value"]: v["count"] for v in classcode["top_values"]}
        self.assertEqual(values, {"1": 2, "2": 1, "3": 1})

    def test_open_dbf_from_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "shape.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("shape/sample.dbf", self.dbf_bytes)
                zf.writestr("shape/sample.shp", b"dummy")
            raw, name = dbf_inspect._open_dbf_bytes(zip_path, member=None)
            self.assertEqual(raw, self.dbf_bytes)
            self.assertTrue(name.endswith("sample.dbf"))

    def test_cli_help_and_main_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dbf_path = os.path.join(tmpdir, "sample.dbf")
            with open(dbf_path, "wb") as f:
                f.write(self.dbf_bytes)
            json_out = os.path.join(tmpdir, "out.json")
            rc = dbf_inspect.main([dbf_path, "--json-out", json_out, "--quiet"])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(json_out))


class TestGpkgFillRate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "sample.gpkg")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE gpkg_contents ("
            "table_name TEXT, data_type TEXT, identifier TEXT, description TEXT)"
        )
        conn.execute(
            "INSERT INTO gpkg_contents VALUES (?, ?, ?, ?)",
            ("bldg_lod1", "features", "bldg_lod1", "dummy building layer"),
        )
        conn.execute(
            "CREATE TABLE bldg_lod1 ("
            "id INTEGER PRIMARY KEY, storeysBelowGround INTEGER, usage TEXT, name TEXT)"
        )
        rows = [
            (1, 1, "業務施設", "Building A"),
            (2, None, "共同住宅", "Building B"),
            (3, 0, "", None),
            (4, None, None, "Building D"),
        ]
        conn.executemany("INSERT INTO bldg_lod1 VALUES (?, ?, ?, ?)", rows)
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_list_layers(self):
        conn = sqlite3.connect(self.db_path)
        try:
            layers = gpkg_fill_rate.list_layers(conn)
        finally:
            conn.close()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0]["table_name"], "bldg_lod1")

    def test_select_target_layers_default_pattern(self):
        conn = sqlite3.connect(self.db_path)
        try:
            layers = gpkg_fill_rate.list_layers(conn)
        finally:
            conn.close()
        targets = gpkg_fill_rate.select_target_layers(
            layers, gpkg_fill_rate.DEFAULT_LAYER_LIKE, explicit_layer=None
        )
        self.assertEqual(targets, ["bldg_lod1"])

    def test_analyze_layer_fill_rates(self):
        conn = sqlite3.connect(self.db_path)
        try:
            analysis = gpkg_fill_rate.analyze_layer(
                conn, "bldg_lod1", gpkg_fill_rate.DEFAULT_COLUMNS_LIKE
            )
        finally:
            conn.close()
        self.assertEqual(analysis["row_count"], 4)
        by_col = {c["column"]: c for c in analysis["columns"]}

        # storeysBelowGround: 4件中2件が非null（0 も非null扱い）
        self.assertEqual(by_col["storeysBelowGround"]["non_null_count"], 2)
        self.assertAlmostEqual(by_col["storeysBelowGround"]["non_null_rate"], 0.5)
        self.assertTrue(by_col["storeysBelowGround"]["priority"])

        # usage: 4件中3件が非null（うち1件は空文字列なので非空文字は2件）
        self.assertEqual(by_col["usage"]["non_null_count"], 3)
        self.assertEqual(by_col["usage"]["non_empty_count"], 2)

        # id は関心列パターンに一致しないので priority=False
        self.assertFalse(by_col["id"]["priority"])

    def test_main_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_out = os.path.join(tmpdir, "out.json")
            rc = gpkg_fill_rate.main([self.db_path, "--json-out", json_out, "--quiet"])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(json_out))


class TestTileProbe(unittest.TestCase):
    def test_enumerate_tiles_small_bbox(self):
        # zoom=15 で 1 タイル分の幅にほぼ収まる程度の極小 bbox
        bbox = (139.68, 35.60, 139.685, 35.605)
        xy_list = tile_probe.enumerate_tiles(bbox, zoom=15)
        self.assertGreaterEqual(len(xy_list), 1)
        for x, y in xy_list:
            self.assertIsInstance(x, int)
            self.assertIsInstance(y, int)

    def test_build_urls_uses_tiles_module_and_no_network(self):
        bbox = (139.68, 35.60, 139.69, 35.61)
        url_data = tile_probe.build_urls(bbox, zoom=15, layers=["dem5a", "dem1a"])
        self.assertEqual(url_data["zoom"], 15)
        self.assertIn("dem5a", url_data["layers"])
        self.assertIn("dem1a", url_data["layers"])
        self.assertGreater(len(url_data["layers"]["dem5a"]), 0)
        for url in url_data["layers"]["dem5a"]:
            self.assertTrue(
                url.startswith("https://cyberjapandata.gsi.go.jp/xyz/dem5a/15/")
            )
            self.assertTrue(url.endswith(".txt"))

    def test_default_bbox_covers_meguro_and_setagaya_roughly(self):
        # 目黒区役所・世田谷区役所付近の代表点が既定 bbox に含まれることを確認する
        # （厳密な行政界確認ではなく「概算」の妥当性チェック）。
        west, south, east, north = tile_probe.DEFAULT_BBOX
        meguro_ward_office = (139.6983, 35.6412)  # lon, lat（概算）
        setagaya_ward_office = (139.6532, 35.6467)  # lon, lat（概算）
        for lon, lat in (meguro_ward_office, setagaya_ward_office):
            self.assertTrue(west <= lon <= east, f"lon {lon} not in bbox")
            self.assertTrue(south <= lat <= north, f"lat {lat} not in bbox")

    def test_main_without_fetch_does_not_touch_network(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_out = os.path.join(tmpdir, "out.json")
            rc = tile_probe.main(
                [
                    "--bbox",
                    "139.68,35.60,139.69,35.61",
                    "--zoom",
                    "15",
                    "--layers",
                    "dem5a",
                    "--json-out",
                    json_out,
                    "--quiet",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(json_out))


class TestDepthClassCheck(unittest.TestCase):
    def _dbf_field(self, values_with_counts: dict, unique_count: int | None = None) -> dict:
        top_values = [{"value": v, "count": c} for v, c in values_with_counts.items()]
        return {
            "name": "CLASSCODE",
            "unique_count": unique_count if unique_count is not None else len(top_values),
            "top_values": top_values,
        }

    def test_all_codes_known(self):
        field_stats = self._dbf_field({"1": 10, "2": 5, "3": 2})
        source_entry = {
            "class_codes": {"1": [0.0, 0.1], "2": [0.1, 0.5], "3": [0.5, 1.0]},
            "verified": True,
            "source_url": "https://example.invalid/dummy",
        }
        result = depth_class_check.compare(field_stats, source_entry)
        self.assertEqual(result["unmapped_in_data"], [])
        self.assertEqual(result["unused_in_table"], [])

    def test_unknown_code_detected(self):
        field_stats = self._dbf_field({"1": 10, "2": 5, "9": 1})
        source_entry = {
            "class_codes": {"1": [0.0, 0.1], "2": [0.1, 0.5], "3": [0.5, 1.0]},
            "verified": False,
            "source_url": None,
        }
        result = depth_class_check.compare(field_stats, source_entry)
        unmapped_values = [item["value"] for item in result["unmapped_in_data"]]
        self.assertEqual(unmapped_values, ["9"])
        self.assertEqual(result["unused_in_table"], ["3"])

    def test_compare_against_repo_depth_class_tables_json(self):
        # 実際の pipelines/config/depth_class_tables.json を読み込めることを確認する
        # （フォーマットの整合性チェックを兼ねる）。
        tables = depth_class_check.load_tables(depth_class_check._DEFAULT_TABLES_PATH)
        source_entry = depth_class_check.get_source_entry(tables, "tokyo_inundation_map")
        field_stats = self._dbf_field({"1": 5, "2": 5, "99": 1})
        result = depth_class_check.compare(field_stats, source_entry)
        unmapped_values = [item["value"] for item in result["unmapped_in_data"]]
        self.assertIn("99", unmapped_values)
        self.assertNotIn("1", unmapped_values)

    def test_unknown_source_raises(self):
        tables = {"sources": {"a": {"class_codes": {}}}}
        with self.assertRaises(depth_class_check.CheckError):
            depth_class_check.get_source_entry(tables, "does_not_exist")


if __name__ == "__main__":
    unittest.main()
