"""docs/03_スコアリング仕様.md に対するスコアリングエンジンのテスト。"""
from __future__ import annotations

import unittest

from floodbcp.measures import load_measures_config
from floodbcp.scoring import (
    _compute_priority,
    assess,
    load_scoring_config,
)

from helpers import FIXED_COMPUTED_AT, make_feature

CONFIG = load_scoring_config()
MEASURES = load_measures_config()


def run(feature, answers=None):
    return assess(feature, answers=answers, config=CONFIG, measures_config=MEASURES, computed_at=FIXED_COMPUTED_AT)


class HGradeTests(unittest.TestCase):
    """3-2 基本等級の閾値境界と 3-3 補正・オーバーライド。"""

    def _h_for_inland(self, min_m, max_m=None):
        f = make_feature(
            inland_depth_min_m=min_m,
            inland_depth_max_m=max_m if max_m is not None else min_m,
            river_depth_min_m=None,
            river_depth_max_m=None,
        )
        return run(f).H

    def test_zero_depth_with_data_is_grade_0(self):
        self.assertEqual(self._h_for_inland(0.0, 0.0), 0)

    def test_boundaries(self):
        cases = [
            (0.49, 1),
            (0.5, 2),
            (0.99, 2),
            (1.0, 3),
            (2.99, 3),
            (3.0, 4),
        ]
        for depth, expected in cases:
            with self.subTest(depth=depth):
                self.assertEqual(self._h_for_inland(depth), expected)

    def test_correction_capped_at_plus1_even_if_multiple_conditions_true(self):
        f = make_feature(
            inland_depth_min_m=0.3,
            inland_depth_max_m=0.3,
            river_depth_min_m=None,
            river_depth_max_m=None,
            flood_history_flag=True,
            depression_flag=True,
            landform_class="旧河道",
        )
        result = run(f)
        # base grade(0.3) = 1。3条件すべて真でも補正は +1 まで -> H=2（+3なら4になってしまう）。
        self.assertEqual(result.H, 2)

    def test_zero_grade_with_history_becomes_grade_2(self):
        f = make_feature(
            inland_depth_min_m=0.0,
            inland_depth_max_m=0.0,
            river_depth_min_m=None,
            river_depth_max_m=None,
            flood_history_flag=True,
        )
        result = run(f)
        self.assertEqual(result.H, 2)

    def test_no_depth_data_but_history_gives_provisional_grade_2_and_status_assessed(self):
        f = make_feature(
            inland_depth_min_m=None,
            inland_depth_max_m=None,
            river_depth_min_m=None,
            river_depth_max_m=None,
            flood_history_flag=True,
        )
        result = run(f)
        self.assertEqual(result.status, "assessed")
        self.assertEqual(result.H, 2)

    def test_surge_only_data_is_assessed_and_h_from_surge_min(self):
        # 内水・洪水は null でも、高潮（surge）データが単独であれば H は算出可能
        # （insufficient_data にはならない）。depth_rep は surge の下限値を使う。
        f = make_feature(
            inland_depth_min_m=None,
            inland_depth_max_m=None,
            river_depth_min_m=None,
            river_depth_max_m=None,
            surge_depth_min_m=1.0,
            surge_depth_max_m=2.0,
            flood_history_flag=False,
            depression_flag=False,
        )
        result = run(f)
        self.assertEqual(result.status, "assessed")
        self.assertEqual(result.H, 3)  # depth_rep=1.0 -> base grade 3、補正なし

    def test_max_grade_capped_at_4(self):
        # depth_rep 5.0 は base grade 4。補正 +1 があっても上限4を超えない。
        f = make_feature(
            inland_depth_min_m=5.0,
            inland_depth_max_m=6.0,
            river_depth_min_m=None,
            river_depth_max_m=None,
            flood_history_flag=True,
        )
        result = run(f)
        self.assertEqual(result.H, 4)


class VGradeTests(unittest.TestCase):
    """4章 流入脆弱性等級 V（Tier0基礎点・加減点・Tier1上書き）。"""

    def test_base_by_storeys_below(self):
        cases = [(0, 0), (1, 2), (2, 3), (5, 3)]
        for storeys_below, expected in cases:
            with self.subTest(storeys_below=storeys_below):
                f = make_feature(storeys_below=storeys_below)
                self.assertEqual(run(f).V, expected)

    def test_unknown_storeys_below_estimate(self):
        # other は延床>=3000でないと対象外(out_of_scope)になるため、3000以上にしておく。
        # 4-2 の加減点（延床>=3000 で+1、usage_class=station で+1）は
        # storeys_below が不明でも独立に適用されるため、その分を織り込んだ期待値にする。
        cases = [
            ("commercial_large", None, 2),  # base2、加点なし
            ("station", None, 3),  # base2 + station加点(+1)
            ("hospital", None, 2),  # base2、加点なし
            ("residential_large", None, 2),  # base2、加点なし
            ("office", 15000, 3),  # base2(延床>=10000) + 延床>=3000加点(+1)
            ("office", 5000, 2),  # base1(その他扱い) + 延床>=3000加点(+1)
            ("other", 4000, 2),  # base1(その他扱い) + 延床>=3000加点(+1)
        ]
        for usage_class, floor_area, expected in cases:
            with self.subTest(usage_class=usage_class, floor_area=floor_area):
                f = make_feature(
                    usage_class=usage_class,
                    storeys_below=None,
                    total_floor_area_m2=floor_area,
                )
                self.assertEqual(run(f).V, expected)

    def test_adjustment_electric_room_is_single_plus1_even_if_both_subconditions_true(self):
        f = make_feature(storeys_below=0, total_floor_area_m2=5000, storeys_above=8)
        self.assertEqual(run(f).V, 1)

    def test_adjustment_below_road(self):
        f = make_feature(storeys_below=0, rel_elev_m=-0.5)
        self.assertEqual(run(f).V, 1)

    def test_adjustment_post_guideline_year_is_minus1(self):
        f = make_feature(storeys_below=1, year_built=2022)
        self.assertEqual(run(f).V, 1)  # base2 - 1

    def test_adjustment_station_usage(self):
        f = make_feature(storeys_below=0, usage_class="station")
        self.assertEqual(run(f).V, 1)

    def test_clamped_to_max_4(self):
        f = make_feature(storeys_below=2, total_floor_area_m2=5000, rel_elev_m=-0.5, usage_class="station")
        self.assertEqual(run(f).V, 4)

    def test_tier1_q3_yes_forces_v_4(self):
        f = make_feature(storeys_below=0)
        answers = {"q03": "yes"}
        self.assertEqual(run(f, answers).V, 4)

    def test_tier1_stopwater_three_conditions_minus2(self):
        f = make_feature(storeys_below=2)  # base V=3
        answers = {"q07": "yes", "q08": "yes", "q09": "yes"}
        self.assertEqual(run(f, answers).V, 1)

    def test_tier1_stopwater_partial_minus1(self):
        f = make_feature(storeys_below=2)  # base V=3
        answers = {"q07": "yes", "q08": "no", "q09": "yes"}
        self.assertEqual(run(f, answers).V, 2)

    def test_tier1_q1_no_resets_base_to_0(self):
        f = make_feature(storeys_below=2)
        answers = {"q01": "no"}
        self.assertEqual(run(f, answers).V, 0)

    def test_tier1_q2_yes_plus1(self):
        f = make_feature(storeys_below=0)
        answers = {"q02": "yes"}
        self.assertEqual(run(f, answers).V, 1)

    def test_tier1_q6_yes_minus1(self):
        f = make_feature(storeys_below=1)  # base2
        answers = {"q06": "yes"}
        self.assertEqual(run(f, answers).V, 1)

    def test_tier1_q10_yes_plus1_capped_at_4(self):
        f = make_feature(storeys_below=2, total_floor_area_m2=5000, rel_elev_m=-0.5)  # tier0 -> 4 (capped)
        answers = {"q10": "yes"}
        self.assertEqual(run(f, answers).V, 4)

    def test_tier1_q3_no_q4_yes_q5_no_caps_at_1(self):
        f = make_feature(storeys_below=2, total_floor_area_m2=5000, rel_elev_m=-0.5)  # tier0 -> 4
        answers = {"q03": "no", "q04": "yes", "q05": "no"}
        self.assertEqual(run(f, answers).V, 1)


class IGradeTests(unittest.TestCase):
    """5章 事業影響度等級 I。"""

    def test_base_table(self):
        cases = [
            ("hospital", None, None, 4),
            ("datacenter", None, None, 4),
            ("public_critical", None, None, 4),
            ("station", 80000, None, 4),
            ("station", 1000, None, 3),
            ("station", None, None, 3),
            ("commercial_large", None, None, 3),
            ("welfare", None, None, 3),
            ("logistics", None, 12000, 3),
            ("logistics", None, 4000, 2),
            ("office", None, 12000, 2),
            ("commercial", None, None, 2),
            ("school", None, None, 2),
            ("residential_large", None, None, 2),
            ("office", None, 2000, 1),
            ("other", None, 4000, 1),
        ]
        for usage_class, ridership, floor_area, expected in cases:
            with self.subTest(usage_class=usage_class, ridership=ridership, floor_area=floor_area):
                f = make_feature(
                    usage_class=usage_class,
                    station_ridership=ridership,
                    total_floor_area_m2=floor_area,
                )
                self.assertEqual(run(f).I, expected)

    def test_additions_and_cap(self):
        f = make_feature(usage_class="office", total_floor_area_m2=2000, alt_facility_dist_m=1500)
        answers = {"q12": "yes", "q10": "yes"}
        # base1 + alt(1) + q12(1) + q10(1) = 4 = 上限ちょうど
        self.assertEqual(run(f, answers).I, 4)

    def test_cap_does_not_exceed_4_from_high_base(self):
        f = make_feature(usage_class="hospital", alt_facility_dist_m=2000)
        self.assertEqual(run(f).I, 4)


class CConfidenceTests(unittest.TestCase):
    """7章 データ確信度 C。"""

    def test_full_weight_sum_is_100(self):
        f = make_feature()
        answers = {f"q{i:02d}": "yes" for i in range(1, 11)}
        result = run(f, answers)
        self.assertEqual(result.C, 100)

    def test_inland_class_width_deduction(self):
        # baseline（Tier1なし）は 80。内水階級幅 3.0m（>=2.5m）で -10。
        f = make_feature(inland_depth_min_m=0.0, inland_depth_max_m=3.0)
        result = run(f)
        self.assertEqual(result.C, 80 - 10)

    def test_hazard_age_deduction(self):
        # baseline（Tier1なし）は 80。hazard_source_year=2010, as_of=2026 -> 16年で -10。
        f = make_feature(hazard_source_year=2010)
        result = run(f)
        self.assertEqual(result.C, 80 - 10)

    def test_floor_is_0_when_no_data(self):
        f = make_feature(
            usage_class=None,
            storeys_below=None,
            storeys_above=None,
            total_floor_area_m2=None,
            inland_depth_min_m=None,
            inland_depth_max_m=None,
            river_depth_min_m=None,
            river_depth_max_m=None,
            rel_elev_m=None,
            flood_history_flag=True,  # insufficient_data を避け assessed のまま計算させる
        )
        result = run(f)
        self.assertEqual(result.C, 0)


class MatrixTests(unittest.TestCase):
    """8章 P = H×V マトリクス、9章 優先度 = P×I マトリクスを表のまま検証。"""

    EXPECTED_P = [
        [0, 0, 0, 0, 0],
        [0, 1, 2, 3, 3],
        [1, 2, 3, 4, 4],
        [2, 3, 3, 4, 4],
        [2, 3, 4, 4, 4],
    ]

    EXPECTED_PRIORITY = [
        ["D", "D", "D", "C", "C"],
        ["D", "D", "C", "C", "B"],
        ["D", "C", "C", "B", "B"],
        ["C", "C", "B", "A", "A"],
        ["C", "B", "A", "A", "A"],
    ]

    def test_p_matrix_all_cells(self):
        rows = CONFIG["p_matrix"]["rows"]
        for h in range(5):
            for v in range(5):
                with self.subTest(H=h, V=v):
                    self.assertEqual(rows[h][v], self.EXPECTED_P[h][v])

    def test_priority_matrix_all_cells(self):
        rows = CONFIG["priority_matrix"]["rows"]
        for p in range(5):
            for i in range(5):
                with self.subTest(P=p, I=i):
                    self.assertEqual(rows[p][i], self.EXPECTED_PRIORITY[p][i])

    def test_low_confidence_raises_priority_and_marks_asterisk(self):
        raise_cfg = CONFIG["priority_low_confidence_raise"]
        priority_cfg = CONFIG["priority_matrix"]
        label, raised = _compute_priority(2, 0, 10, priority_cfg, raise_cfg)  # base "D" -> "C*"
        self.assertEqual(label, "C*")
        self.assertTrue(raised)

    def test_low_confidence_does_not_raise_when_c_at_threshold(self):
        raise_cfg = CONFIG["priority_low_confidence_raise"]
        priority_cfg = CONFIG["priority_matrix"]
        label, raised = _compute_priority(2, 0, 50, priority_cfg, raise_cfg)  # C=50 は「C<50」に該当しない
        self.assertEqual(label, "D")
        self.assertFalse(raised)

    def test_low_confidence_does_not_raise_when_p_below_min(self):
        raise_cfg = CONFIG["priority_low_confidence_raise"]
        priority_cfg = CONFIG["priority_matrix"]
        label, raised = _compute_priority(1, 0, 10, priority_cfg, raise_cfg)  # P=1 < min_p(2)
        self.assertEqual(label, "D")
        self.assertFalse(raised)

    def test_raise_at_top_priority_a_stays_a(self):
        raise_cfg = CONFIG["priority_low_confidence_raise"]
        priority_cfg = CONFIG["priority_matrix"]
        label, raised = _compute_priority(4, 4, 10, priority_cfg, raise_cfg)  # already "A"
        self.assertEqual(label, "A")
        self.assertFalse(raised)


class StatusTests(unittest.TestCase):
    """10章 評価ステータス。"""

    def test_residential_is_out_of_scope(self):
        f = make_feature(usage_class="residential")
        result = run(f)
        self.assertEqual(result.status, "out_of_scope")
        self.assertIsNone(result.H)
        self.assertIsNone(result.priority)

    def test_other_below_3000_is_out_of_scope(self):
        f = make_feature(usage_class="other", total_floor_area_m2=2999)
        self.assertEqual(run(f).status, "out_of_scope")

    def test_other_at_3000_is_in_scope(self):
        f = make_feature(usage_class="other", total_floor_area_m2=3000)
        self.assertEqual(run(f).status, "assessed")

    def test_insufficient_data_when_no_depth_and_no_flags(self):
        # 内水・洪水・高潮の「すべて」が null（かつ実績・窪地フラグなし）で insufficient_data。
        f = make_feature(
            inland_depth_min_m=None,
            inland_depth_max_m=None,
            river_depth_min_m=None,
            river_depth_max_m=None,
            surge_depth_min_m=None,
            surge_depth_max_m=None,
            flood_history_flag=False,
            depression_flag=False,
        )
        result = run(f)
        self.assertEqual(result.status, "insufficient_data")
        self.assertIsNone(result.H)
        self.assertIsNone(result.P)

    def test_surge_only_is_not_insufficient_data(self):
        # 内水・洪水が null でも、高潮（surge）データが1つでもあれば insufficient_data にならない。
        f = make_feature(
            inland_depth_min_m=None,
            inland_depth_max_m=None,
            river_depth_min_m=None,
            river_depth_max_m=None,
            surge_depth_min_m=1.0,
            surge_depth_max_m=2.0,
            flood_history_flag=False,
            depression_flag=False,
        )
        result = run(f)
        self.assertEqual(result.status, "assessed")
        self.assertIsNotNone(result.H)
        self.assertIsNotNone(result.priority)


class ScenarioTests(unittest.TestCase):
    """タスクカード指定のシナリオ。"""

    def test_jiyugaoka_style_scenario_is_priority_a(self):
        f = make_feature(
            usage_class="commercial_large",
            storeys_below=1,
            total_floor_area_m2=12000,
            inland_depth_min_m=0.5,
            inland_depth_max_m=1.0,
            river_depth_min_m=None,
            river_depth_max_m=None,
            flood_history_flag=True,
        )
        result = run(f)
        self.assertEqual(result.priority, "A")

    def test_hospital_no_basement_no_hazard_is_d_or_c(self):
        f = make_feature(
            usage_class="hospital",
            hospital_flag=True,
            storeys_below=0,
            inland_depth_min_m=0.0,
            inland_depth_max_m=0.0,
            river_depth_min_m=0.0,
            river_depth_max_m=0.0,
        )
        result = run(f)
        self.assertIn(result.priority, ("D", "C"))


if __name__ == "__main__":
    unittest.main()
