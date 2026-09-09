"""floodbcp/report.py の FR-11 レポート出力（優先現地調査リスト・管理施設一覧）のテスト。"""
from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from floodbcp.report import (
    FACILITY_LIST_FIELDS,
    PRIORITY_LIST_FIELDS,
    main_factors_ja,
    write_facility_list_csv,
    write_priority_list_csv,
)


def _assessment(building_id, *, status="assessed", priority=None, P=None, H=None, V=None, I=None, C=None, **overrides):
    base = dict(
        building_id=building_id,
        tier=0,
        score_version="0.1.0",
        data_version="test_v0",
        computed_at="2026-09-09T00:00:00Z",
        status=status,
        H=H,
        V=V,
        I=I,
        P=P,
        C=C,
        priority=priority,
        priority_raised_by_low_confidence=bool(priority and str(priority).endswith("*")),
        evidence=[],
        missing_info=[],
        priority_checks=[],
        measures=[],
    )
    base.update(overrides)
    return base


def _read_csv_bytes(path: Path) -> tuple[bytes, list[dict[str, str]]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    return raw, rows


class PriorityListOrderingTests(unittest.TestCase):
    def test_sorted_priority_then_p_desc_then_c_asc(self):
        assessments = [
            _assessment("bldg_b_low_p", priority="B", P=2, C=50),
            _assessment("bldg_a_star", priority="A*", P=3, C=40),
            _assessment("bldg_a_high_p", priority="A", P=4, C=60),
            _assessment("bldg_c_excluded", priority="C", P=1, C=90),
            _assessment("bldg_out_of_scope", status="out_of_scope"),
            _assessment("bldg_a_high_p_low_c", priority="A", P=4, C=20),
            _assessment("bldg_b_star", priority="B*", P=1, C=10),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv(assessments, path)
            _, rows = _read_csv_bytes(path)

        ids = [r["building_id"] for r in rows]
        # A (P=4,C=20) -> A (P=4,C=60) -> A* -> B -> B*
        self.assertEqual(
            ids,
            ["bldg_a_high_p_low_c", "bldg_a_high_p", "bldg_a_star", "bldg_b_low_p", "bldg_b_star"],
        )
        # C/D/out_of_scope は優先現地調査リストから除外される
        self.assertNotIn("bldg_c_excluded", ids)
        self.assertNotIn("bldg_out_of_scope", ids)

    def test_header_matches_spec_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv([_assessment("bldg_1", priority="A", P=4, C=50)], path)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(list(rows[0].keys()), PRIORITY_LIST_FIELDS)

    def test_utf8_bom_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv([_assessment("bldg_1", priority="A", P=4, C=50)], path)
            raw = path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "CSV should start with a UTF-8 BOM (Excel向け)")

    def test_priority_checks_and_measures_semicolon_joined(self):
        assessments = [
            _assessment(
                "bldg_1",
                priority="A",
                P=4,
                C=50,
                priority_checks=["受変電設備の設置階", "全館停止波及の有無"],
                measures=["M-01", "M-07", "M-10"],
            )
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv(assessments, path)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(rows[0]["priority_checks"], "受変電設備の設置階;全館停止波及の有無")
        self.assertEqual(rows[0]["measures"], "M-01;M-07;M-10")

    def test_features_by_id_fills_name_and_usage_class(self):
        assessments = [_assessment("bldg_1", priority="A", P=4, C=50)]
        features_by_id = {"bldg_1": {"name": "架空:テスト棟", "usage_class": "office", "ward_code": "13110"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv(assessments, path, features_by_id=features_by_id)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(rows[0]["name"], "架空:テスト棟")
        self.assertEqual(rows[0]["usage_class"], "office")

    def test_missing_features_by_id_leaves_name_blank(self):
        assessments = [_assessment("bldg_unknown", priority="A", P=4, C=50)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "priority.csv"
            write_priority_list_csv(assessments, path)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(rows[0]["name"], "")


class MainFactorsTests(unittest.TestCase):
    def test_picks_one_per_axis_up_to_three_joined_by_semicolon(self):
        evidence = [
            {"axis": "H", "rule": "depth_rep", "value": "0.5 m -> base grade 2", "source": "s", "fetched_at": None},
            {"axis": "H", "rule": "correction_history", "value": "flood_history_flag = true", "source": "s", "fetched_at": None},
            {"axis": "V", "rule": "storeys_below", "value": 1, "source": "s", "fetched_at": None},
            {"axis": "I", "rule": "usage_class_base", "value": "usage_class=office -> base I=1", "source": "s", "fetched_at": None},
            {"axis": "C", "rule": "weight_inland_data", "value": 20, "source": None, "fetched_at": None},
        ]
        result = main_factors_ja(evidence)
        parts = result.split(";")
        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[0].startswith("H:"))
        self.assertTrue(parts[1].startswith("V:"))
        self.assertTrue(parts[2].startswith("I:"))
        # C axis のエントリは含まれない
        self.assertNotIn("C:", result)
        # ラベルは日本語（既知の rule には日本語の要因説明が付く）
        self.assertIn("浸水想定深による基礎等級", parts[0])
        self.assertIn("地下階数", parts[1])
        self.assertIn("用途分類による基礎影響度", parts[2])

    def test_missing_axis_is_skipped_not_padded(self):
        evidence = [{"axis": "H", "rule": "depth_rep", "value": "1.0 m", "source": None, "fetched_at": None}]
        result = main_factors_ja(evidence)
        self.assertEqual(len(result.split(";")), 1)

    def test_empty_evidence_returns_empty_string(self):
        self.assertEqual(main_factors_ja([]), "")
        self.assertEqual(main_factors_ja(None), "")

    def test_unknown_rule_falls_back_gracefully(self):
        evidence = [{"axis": "H", "rule": "some_future_rule", "value": "x", "source": None, "fetched_at": None}]
        result = main_factors_ja(evidence)
        self.assertTrue(result.startswith("H:"))
        self.assertIn("some_future_rule", result)


class FacilityListTests(unittest.TestCase):
    def test_includes_all_statuses_in_input_order(self):
        assessments = [
            _assessment("bldg_1", priority="A", P=4, H=3, V=3, I=4, C=70),
            _assessment("bldg_2", status="out_of_scope"),
            _assessment("bldg_3", status="insufficient_data", V=1, I=2, C=40),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facilities.csv"
            write_facility_list_csv(assessments, path)
            _, rows = _read_csv_bytes(path)
        self.assertEqual([r["building_id"] for r in rows], ["bldg_1", "bldg_2", "bldg_3"])
        self.assertEqual(rows[1]["status"], "out_of_scope")
        self.assertEqual(rows[1]["priority"], "")

    def test_header_matches_spec_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facilities.csv"
            write_facility_list_csv([_assessment("bldg_1", priority="A", P=4, C=50)], path)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(list(rows[0].keys()), FACILITY_LIST_FIELDS)

    def test_utf8_bom_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facilities.csv"
            write_facility_list_csv([_assessment("bldg_1")], path)
            raw = path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))

    def test_features_by_id_fills_ward_code(self):
        assessments = [_assessment("bldg_1", priority="A", P=4, C=50)]
        features_by_id = {"bldg_1": {"name": "架空:テスト棟", "usage_class": "office", "ward_code": "13112"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facilities.csv"
            write_facility_list_csv(assessments, path, features_by_id=features_by_id)
            _, rows = _read_csv_bytes(path)
        self.assertEqual(rows[0]["ward_code"], "13112")


class ReportCliEndToEndTests(unittest.TestCase):
    """floodbcp report CLI サブコマンドの結合テスト（サンプルデータ使用）。"""

    def test_report_cli_produces_two_csvs_with_priority_a_before_b(self):
        import subprocess
        import sys

        repo_root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "out.json"
            priority_csv = Path(tmp) / "priority.csv"
            facility_csv = Path(tmp) / "facilities.csv"

            assess_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "floodbcp",
                    "assess",
                    "--features",
                    str(repo_root / "data" / "samples" / "features_sample.csv"),
                    "--answers",
                    str(repo_root / "data" / "samples" / "answers_sample.csv"),
                    "--out",
                    str(out_json),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(assess_result.returncode, 0, msg=assess_result.stderr)

            report_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "floodbcp",
                    "report",
                    "--assessments",
                    str(out_json),
                    "--features",
                    str(repo_root / "data" / "samples" / "features_sample.csv"),
                    "--priority-list",
                    str(priority_csv),
                    "--facility-list",
                    str(facility_csv),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(report_result.returncode, 0, msg=report_result.stderr)
            self.assertTrue(priority_csv.exists())
            self.assertTrue(facility_csv.exists())

            _, priority_rows = _read_csv_bytes(priority_csv)
            _, facility_rows = _read_csv_bytes(facility_csv)

            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(len(facility_rows), len(data))

            base_priorities = [r["priority"].rstrip("*") for r in priority_rows]
            first_b_index = next((i for i, p in enumerate(base_priorities) if p == "B"), len(base_priorities))
            self.assertTrue(
                all(p == "A" for p in base_priorities[:first_b_index]),
                msg=f"A の後にBが来る前提が崩れている: {base_priorities}",
            )
            self.assertIn("A", base_priorities)
            self.assertIn("B", base_priorities)


if __name__ == "__main__":
    unittest.main()
