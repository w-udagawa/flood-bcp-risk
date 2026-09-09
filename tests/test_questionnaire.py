"""questionnaire.py（Tier1 回答 CSV 読込）のテスト。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from floodbcp.questionnaire import QUESTION_IDS, QuestionnaireError, load_answers_csv


class QuestionnaireTests(unittest.TestCase):
    def test_load_and_normalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            header = "building_id," + ",".join(QUESTION_IDS)
            path.write_text(
                header + "\n" + "bldg_a," + ",".join(["yes"] * 12) + "\n" + "bldg_b,no,,unknown,,,,,,,,,\n",
                encoding="utf-8",
            )
            answers = load_answers_csv(path)
        self.assertEqual(answers["bldg_a"]["q01"], "yes")
        self.assertEqual(answers["bldg_a"]["q12"], "yes")
        self.assertEqual(answers["bldg_b"]["q01"], "no")
        self.assertEqual(answers["bldg_b"]["q02"], "unknown")  # 空欄 -> unknown
        self.assertEqual(answers["bldg_b"]["q03"], "unknown")

    def test_invalid_value_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            header = "building_id," + ",".join(QUESTION_IDS)
            path.write_text(header + "\n" + "bldg_a,maybe," + ",".join(["unknown"] * 11) + "\n", encoding="utf-8")
            with self.assertRaises(QuestionnaireError):
                load_answers_csv(path)

    def test_missing_building_id_column_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            path.write_text("q01,q02\nyes,no\n", encoding="utf-8")
            with self.assertRaises(QuestionnaireError):
                load_answers_csv(path)


if __name__ == "__main__":
    unittest.main()
