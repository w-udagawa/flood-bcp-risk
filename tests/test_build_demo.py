"""scripts/build_demo.py のテスト（一時ディレクトリに生成し、決定性・整合性を検証する）。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_demo import DEFAULT_ANSWERS_CSV, DEFAULT_FEATURES_CSV, build  # noqa: E402


def _run_build(out_dir: Path) -> dict:
    return build(
        features_path=DEFAULT_FEATURES_CSV,
        answers_path=DEFAULT_ANSWERS_CSV,
        assessments_out=out_dir / "assessments_sample.json",
        buildings_out=out_dir / "buildings_sample.geojson",
        measures_out=out_dir / "measures.json",
    )


class BuildDemoTests(unittest.TestCase):
    def test_generates_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = _run_build(out_dir)
            self.assertTrue((out_dir / "assessments_sample.json").exists())
            self.assertTrue((out_dir / "buildings_sample.geojson").exists())
            self.assertTrue((out_dir / "measures.json").exists())
            self.assertGreater(summary["building_count"], 0)

    def test_building_id_sets_match_between_geojson_and_assessments(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)

            assessments = json.loads((out_dir / "assessments_sample.json").read_text(encoding="utf-8"))
            buildings = json.loads((out_dir / "buildings_sample.geojson").read_text(encoding="utf-8"))

            assessment_ids = {a["building_id"] for a in assessments}
            building_ids = {f["properties"]["building_id"] for f in buildings["features"]}
            self.assertEqual(assessment_ids, building_ids)
            self.assertEqual(len(assessments), len(buildings["features"]))
            self.assertGreater(len(assessments), 0)

    def test_assessments_have_full_schema_keys(self):
        expected_keys = {
            "building_id",
            "tier",
            "score_version",
            "data_version",
            "computed_at",
            "status",
            "H",
            "V",
            "I",
            "P",
            "C",
            "priority",
            "priority_raised_by_low_confidence",
            "evidence",
            "missing_info",
            "priority_checks",
            "measures",
        }
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            assessments = json.loads((out_dir / "assessments_sample.json").read_text(encoding="utf-8"))
            for a in assessments:
                self.assertEqual(set(a.keys()), expected_keys)

    def test_building_geojson_properties_match_join_js_contract(self):
        expected_props = {"building_id", "name", "usage_class", "ward_code", "storeys_below", "total_floor_area_m2"}
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            buildings = json.loads((out_dir / "buildings_sample.geojson").read_text(encoding="utf-8"))
            self.assertEqual(buildings["type"], "FeatureCollection")
            for feature in buildings["features"]:
                self.assertEqual(feature["type"], "Feature")
                self.assertEqual(feature["geometry"]["type"], "Polygon")
                self.assertEqual(set(feature["properties"].keys()), expected_props)
                # 閉じたリング（始点=終点）であること
                ring = feature["geometry"]["coordinates"][0]
                self.assertEqual(ring[0], ring[-1])
                self.assertEqual(len(ring), 5)

    def test_no_insufficient_data_status_in_web_output(self):
        """insufficient_data は priority が必ず null になり、web/tests/join.test.js の
        前提（out_of_scope 以外は priority が A/B/C/D）と食い違うため除外される。"""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            assessments = json.loads((out_dir / "assessments_sample.json").read_text(encoding="utf-8"))
            statuses = {a["status"] for a in assessments}
            self.assertNotIn("insufficient_data", statuses)
            # ただし out_of_scope（priority が null でも許容される）は残る
            self.assertIn("out_of_scope", statuses)

    def test_polygons_are_within_radius_of_center(self):
        import math

        from scripts.build_demo import CENTER_LAT, CENTER_LON, RADIUS_M

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            buildings = json.loads((out_dir / "buildings_sample.geojson").read_text(encoding="utf-8"))
            for feature in buildings["features"]:
                ring = feature["geometry"]["coordinates"][0]
                lon0, lat0 = ring[0]
                dlat_m = (lat0 - CENTER_LAT) * 111_320.0
                dlon_m = (lon0 - CENTER_LON) * 111_320.0 * math.cos(math.radians(CENTER_LAT))
                dist = math.hypot(dlat_m, dlon_m)
                # 建物中心 + 矩形半径ぶんの余裕を見て、中心から極端に離れていないことだけ確認する
                self.assertLess(dist, RADIUS_M + 100)

    def test_measures_json_derived_from_config_measures(self):
        from floodbcp.measures import load_measures_config

        config = load_measures_config()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            measures = json.loads((out_dir / "measures.json").read_text(encoding="utf-8"))
            self.assertEqual(measures["score_version"], config["score_version"])
            got_ids = [m["id"] for m in measures["measures"]]
            want_ids = [m["id"] for m in config["measures"]]
            self.assertEqual(got_ids, want_ids)
            for got, want in zip(measures["measures"], config["measures"]):
                self.assertEqual(got["title"], want["title"])
                self.assertIn("condition", got)

    def test_deterministic_across_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            _run_build(Path(tmp1))
            _run_build(Path(tmp2))
            for name in ("assessments_sample.json", "buildings_sample.geojson", "measures.json"):
                content1 = (Path(tmp1) / name).read_bytes()
                content2 = (Path(tmp2) / name).read_bytes()
                self.assertEqual(content1, content2, msg=f"{name} is not deterministic across two runs")

    def test_no_real_facility_names_marker(self):
        """サンプルは架空であることの簡易チェック（"架空:" 接頭辞または "サンプル" を含む）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            _run_build(out_dir)
            buildings = json.loads((out_dir / "buildings_sample.geojson").read_text(encoding="utf-8"))
            for feature in buildings["features"]:
                name = feature["properties"]["name"]
                self.assertTrue(
                    "架空" in name or "サンプル" in name,
                    msg=f"name does not carry a fictional-data marker: {name!r}",
                )


if __name__ == "__main__":
    unittest.main()
