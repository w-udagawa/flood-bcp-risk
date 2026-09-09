"""measures.py（対策候補、docs/03_スコアリング仕様.md 第13章）のテスト。"""
from __future__ import annotations

import unittest

from floodbcp.measures import evaluate_measures, load_measures_config
from floodbcp.rules import Context

MEASURES = load_measures_config()


def ctx(**overrides):
    base = dict(
        features={"footprint_area_m2": None, "depression_flag": False, "rel_elev_m": None},
        answers={f"q{i:02d}": "unknown" for i in range(1, 13)},
        scores={"H": 0, "V": 0, "I": 0, "P": 0, "C": 100},
        meta={"tier1_present": False, "as_of_year": 2026},
    )
    for k, v in overrides.items():
        base[k].update(v) if isinstance(base.get(k), dict) and isinstance(v, dict) else base.__setitem__(k, v)
    return Context(**base)


class MeasureConditionTests(unittest.TestCase):
    def test_m01_requires_v_high_and_no_tier1(self):
        c = ctx(scores={"H": 0, "V": 2, "I": 0, "P": 0, "C": 100}, meta={"tier1_present": False, "as_of_year": 2026})
        self.assertIn("M-01", evaluate_measures(c, MEASURES))

        c2 = ctx(scores={"H": 0, "V": 2, "I": 0, "P": 0, "C": 100}, meta={"tier1_present": True, "as_of_year": 2026})
        self.assertNotIn("M-01", evaluate_measures(c2, MEASURES))

    def test_m07_requires_p_gte_2(self):
        c_low = ctx(scores={"H": 0, "V": 0, "I": 0, "P": 1, "C": 100})
        self.assertNotIn("M-07", evaluate_measures(c_low, MEASURES))
        c_high = ctx(scores={"H": 0, "V": 0, "I": 0, "P": 2, "C": 100})
        self.assertIn("M-07", evaluate_measures(c_high, MEASURES))

    def test_m03_via_q02_yes_or_v_and_h(self):
        c1 = ctx(answers={f"q{i:02d}": "unknown" for i in range(1, 13)} | {"q02": "yes"})
        self.assertIn("M-03", evaluate_measures(c1, MEASURES))

        c2 = ctx(scores={"H": 1, "V": 2, "I": 0, "P": 0, "C": 100})
        self.assertIn("M-03", evaluate_measures(c2, MEASURES))

        c3 = ctx(scores={"H": 0, "V": 0, "I": 0, "P": 0, "C": 100})
        self.assertNotIn("M-03", evaluate_measures(c3, MEASURES))

    def test_m10_requires_i_and_p(self):
        c = ctx(scores={"H": 0, "V": 0, "I": 3, "P": 2, "C": 100})
        self.assertIn("M-10", evaluate_measures(c, MEASURES))
        c2 = ctx(scores={"H": 0, "V": 0, "I": 3, "P": 1, "C": 100})
        self.assertNotIn("M-10", evaluate_measures(c2, MEASURES))


if __name__ == "__main__":
    unittest.main()
