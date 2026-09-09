"""features.py（CSV/JSONL 読込・型変換・スキーマ検証）のテスト。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from floodbcp.features import SchemaError, load_features_csv, load_features_jsonl


class CsvLoadTests(unittest.TestCase):
    def test_type_conversion_and_blank_to_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.csv"
            path.write_text(
                "building_id,storeys_below,total_floor_area_m2,flood_history_flag,name\n"
                "bldg_a,2,1234.5,true,テスト棟\n"
                "bldg_b,,,false,\n",
                encoding="utf-8",
            )
            features = load_features_csv(path)
        self.assertEqual(len(features), 2)
        a, b = features
        self.assertEqual(a.storeys_below, 2)
        self.assertIsInstance(a.storeys_below, int)
        self.assertEqual(a.total_floor_area_m2, 1234.5)
        self.assertIsInstance(a.total_floor_area_m2, float)
        self.assertIs(a.flood_history_flag, True)
        self.assertEqual(a.name, "テスト棟")

        self.assertIsNone(b.storeys_below)
        self.assertIsNone(b.total_floor_area_m2)
        self.assertIs(b.flood_history_flag, False)
        self.assertIsNone(b.name)

    def test_required_building_id_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.csv"
            path.write_text("building_id,name\n,テスト\n", encoding="utf-8")
            with self.assertRaises(SchemaError):
                load_features_csv(path)

    def test_unknown_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.csv"
            path.write_text("building_id,not_a_real_field\nbldg_a,x\n", encoding="utf-8")
            with self.assertRaises(SchemaError):
                load_features_csv(path)

    def test_invalid_boolean_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.csv"
            path.write_text("building_id,flood_history_flag\nbldg_a,maybe\n", encoding="utf-8")
            with self.assertRaises(SchemaError):
                load_features_csv(path)


class JsonlLoadTests(unittest.TestCase):
    def test_load_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.jsonl"
            rows = [
                {"building_id": "bldg_a", "storeys_below": 1, "flood_history_flag": True},
                {"building_id": "bldg_b"},
            ]
            path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
            features = load_features_jsonl(path)
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0].storeys_below, 1)
        self.assertIsNone(features[1].storeys_below)

    def test_unknown_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.jsonl"
            path.write_text(json.dumps({"building_id": "bldg_a", "bogus": 1}), encoding="utf-8")
            with self.assertRaises(SchemaError):
                load_features_jsonl(path)


if __name__ == "__main__":
    unittest.main()
