"""CLI（floodbcp.__main__）のエンドツーエンドテスト。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES_CSV = REPO_ROOT / "data" / "samples" / "features_sample.csv"
ANSWERS_CSV = REPO_ROOT / "data" / "samples" / "answers_sample.csv"


class CliAssessTests(unittest.TestCase):
    def test_assess_end_to_end_produces_json_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "out.json"
            out_csv = Path(tmp) / "out.csv"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "floodbcp",
                    "assess",
                    "--features",
                    str(FEATURES_CSV),
                    "--answers",
                    str(ANSWERS_CSV),
                    "--out",
                    str(out_json),
                    "--csv",
                    str(out_csv),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_csv.exists())

            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(data), 15)

            priorities = {row["priority"] for row in data if row["priority"]}
            statuses = {row["status"] for row in data}
            # 優先度A〜Dが少なくとも1つずつ出ることを確認（* 付きは基底文字で判定）
            base_priorities = {p.rstrip("*") for p in priorities}
            for expected in ("A", "B", "C", "D"):
                self.assertIn(expected, base_priorities, msg=f"priority {expected} not found in sample output")
            self.assertIn("out_of_scope", statuses)
            self.assertIn("insufficient_data", statuses)
            self.assertIn("assessed", statuses)

    def test_explain_prints_karte(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "floodbcp",
                "explain",
                "--features",
                str(FEATURES_CSV),
                "--building-id",
                "bldg_sample_001",
                "--answers",
                str(ANSWERS_CSV),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("bldg_sample_001", result.stdout)
        self.assertIn("優先度", result.stdout)

    def test_import_is_stdlib_only(self):
        result = subprocess.run(
            [sys.executable, "-c", "import floodbcp"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
