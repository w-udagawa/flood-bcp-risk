"""スコアリングエンジン本体。

docs/03_スコアリング仕様.md を実装する。閾値・マトリクス・重みは
config/scoring_v0.1.0.json から読み、ここには「どのフィールドをどう組み合わせるか」
という手続きだけを置く。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .features import Feature
from .measures import evaluate_measures, load_measures_config
from .questionnaire import QUESTION_IDS
from .rules import Context, evaluate_condition, first_match_value, sum_deltas

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent
DEFAULT_SCORING_CONFIG_PATH = _REPO_ROOT / "config" / "scoring_v0.1.0.json"


def load_scoring_config(path: Path | str = DEFAULT_SCORING_CONFIG_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Assessment:
    building_id: str
    tier: int
    score_version: str
    data_version: str | None
    computed_at: str
    status: str
    H: int | None
    V: int | None
    I: int | None
    P: int | None
    C: int | None
    priority: str | None
    priority_raised_by_low_confidence: bool
    evidence: list[dict[str, Any]] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)
    priority_checks: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "building_id": self.building_id,
            "tier": self.tier,
            "score_version": self.score_version,
            "data_version": self.data_version,
            "computed_at": self.computed_at,
            "status": self.status,
            "H": self.H,
            "V": self.V,
            "I": self.I,
            "P": self.P,
            "C": self.C,
            "priority": self.priority,
            "priority_raised_by_low_confidence": self.priority_raised_by_low_confidence,
            "evidence": self.evidence,
            "missing_info": self.missing_info,
            "priority_checks": self.priority_checks,
            "measures": self.measures,
        }


def _normalize_answers(answers: dict[str, str] | None) -> dict[str, str]:
    if answers is None:
        return {q: "unknown" for q in QUESTION_IDS}
    return {q: answers.get(q, "unknown") for q in QUESTION_IDS}


def _determine_status(feature: Feature, status_cfg: dict[str, Any]) -> str:
    usage_class = feature.usage_class
    if usage_class is not None and usage_class in status_cfg["out_of_scope_usage_classes"]:
        return "out_of_scope"
    if usage_class == status_cfg["other_usage_class"]:
        floor = feature.total_floor_area_m2
        threshold = status_cfg["other_min_total_floor_area_m2"]
        if floor is None or floor < threshold:
            return "out_of_scope"
    if (
        feature.inland_depth_min_m is None
        and feature.river_depth_min_m is None
        and feature.flood_history_flag is not True
        and feature.depression_flag is not True
    ):
        return "insufficient_data"
    return "assessed"


def _match_range(value: float, table: list[dict[str, Any]]) -> int:
    for row in table:
        lo, lo_inc = row["min"], row["min_inclusive"]
        hi, hi_inc = row["max"], row["max_inclusive"]
        if lo is not None:
            if lo_inc and value < lo:
                continue
            if not lo_inc and value <= lo:
                continue
        if hi is not None:
            if hi_inc and value > hi:
                continue
            if not hi_inc and value >= hi:
                continue
        return row["grade"]
    raise ValueError(f"H base_grade_table に {value} を満たす行がありません")


def _compute_h(
    feature: Feature, h_cfg: dict[str, Any], meta: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    src = feature.data_versions

    if feature.inland_depth_min_m is None and feature.river_depth_min_m is None:
        # 内水・洪水とも null。ここに到達するのは status != insufficient_data の場合のみ、
        # すなわち flood_history_flag か depression_flag のいずれかが true のとき。
        grade = h_cfg["provisional_grade_when_insufficient_but_evidence"]
        reasons = []
        if feature.flood_history_flag is True:
            reasons.append("flood_history_flag")
        if feature.depression_flag is True:
            reasons.append("depression_flag")
        evidence.append(
            {
                "axis": "H",
                "rule": "provisional_no_depth_data",
                "value": f"H={grade}（暫定: 内水・洪水データなし。根拠: {'/'.join(reasons)}）",
                "source": src,
                "fetched_at": None,
            }
        )
        return grade, evidence

    mins: list[float] = []
    labels: list[str] = []
    for min_field, max_field, label in h_cfg["depth_source_fields"]:
        v = getattr(feature, min_field)
        if v is not None:
            mins.append(v)
            max_v = getattr(feature, max_field)
            labels.append(f"{label}:{v}-{max_v if max_v is not None else '?'}m")
    depth_rep = max(mins)
    base_grade = _match_range(depth_rep, h_cfg["base_grade_table"])
    evidence.append(
        {
            "axis": "H",
            "rule": "depth_rep",
            "value": f"{depth_rep} m -> base grade {base_grade} ({', '.join(labels)})",
            "source": src,
            "fetched_at": None,
        }
    )

    if base_grade == 0 and feature.flood_history_flag is True:
        grade = h_cfg["zero_grade_with_history_override_grade"]
        evidence.append(
            {
                "axis": "H",
                "rule": "zero_grade_history_override",
                "value": f"H={grade}（区域外相当だが浸水実績あり）",
                "source": src,
                "fetched_at": None,
            }
        )
        return grade, evidence

    ctx = Context(features=feature.as_dict(), answers={}, scores={}, meta=meta)
    correction_total, applied = sum_deltas(h_cfg["corrections"], ctx)
    correction = min(correction_total, h_cfg["correction_cap"])
    grade = min(max(base_grade + correction, h_cfg["min"]), h_cfg["max"])
    for a in applied:
        evidence.append(
            {"axis": "H", "rule": f"correction_{a['id']}", "value": a["label"], "source": src, "fetched_at": None}
        )
    if applied:
        evidence.append(
            {
                "axis": "H",
                "rule": "correction_total",
                "value": f"+{correction}（上限{h_cfg['correction_cap']}）",
                "source": src,
                "fetched_at": None,
            }
        )
    return grade, evidence


def _compute_v_base_and_adjust(
    features_dict: dict[str, Any], answers: dict[str, str], scores: dict[str, Any], meta: dict[str, Any], v_cfg: dict[str, Any]
) -> tuple[int, int, list[dict[str, Any]]]:
    ctx = Context(features=features_dict, answers=answers, scores=scores, meta=meta)
    base = first_match_value(v_cfg["base_table"], ctx, default=None)
    if base is None:
        base = first_match_value(
            v_cfg["unknown_estimate_table"], ctx, default=v_cfg["unknown_estimate_table"][-1]["value"]
        )
    delta, applied = sum_deltas(v_cfg["adjustments"], ctx)
    total = min(max(base + delta, v_cfg["min"]), v_cfg["max"])
    return total, base, applied


def _compute_v(
    feature: Feature, answers: dict[str, str], v_cfg: dict[str, Any], scores: dict[str, Any], meta: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    features_dict = feature.as_dict()
    tier1_present = bool(meta.get("tier1_present"))
    evidence: list[dict[str, Any]] = []
    src = feature.data_versions

    v0, base0, applied0 = _compute_v_base_and_adjust(features_dict, answers, scores, meta, v_cfg)
    if feature.storeys_below is not None:
        evidence.append({"axis": "V", "rule": "storeys_below", "value": feature.storeys_below, "source": src, "fetched_at": None})
    else:
        evidence.append(
            {
                "axis": "V",
                "rule": "storeys_below_estimated",
                "value": f"storeys_below 不明 -> usage_class={feature.usage_class} から基礎V={base0} と推定",
                "source": src,
                "fetched_at": None,
            }
        )
    for a in applied0:
        evidence.append({"axis": "V", "rule": f"adjustment_{a['id']}", "value": a["label"], "source": src, "fetched_at": None})

    tcfg = v_cfg["tier1"]
    v_running = v0

    if tier1_present and answers.get("q01") == "no":
        forced_features = {**features_dict, "storeys_below": tcfg["q1_no_reset_base_to"]}
        v_running, base_q1, applied_q1 = _compute_v_base_and_adjust(forced_features, answers, scores, meta, v_cfg)
        evidence.append(
            {
                "axis": "V",
                "rule": "tier1_q01_no_reset_base",
                "value": f"Q1=いいえ -> 基礎V={tcfg['q1_no_reset_base_to']}で再計算 -> V={v_running}",
                "source": None,
                "fetched_at": None,
            }
        )

    if tier1_present and answers.get("q02") == "yes":
        v_running += tcfg["q2_yes_delta"]
        evidence.append({"axis": "V", "rule": "tier1_q02_yes", "value": f"+{tcfg['q2_yes_delta']}", "source": None, "fetched_at": None})

    if tier1_present:
        q7, q8, q9 = answers.get("q07"), answers.get("q08"), answers.get("q09")
        if q7 == "yes" and q8 == "yes" and q9 == "yes":
            v_running += tcfg["q7_q8_q9_all_yes_delta"]
            evidence.append(
                {
                    "axis": "V",
                    "rule": "tier1_q07_full_measures",
                    "value": tcfg["q7_q8_q9_all_yes_delta"],
                    "source": None,
                    "fetched_at": None,
                }
            )
        elif q7 == "yes":
            v_running += tcfg["q7_yes_q8_or_q9_not_yes_delta"]
            evidence.append(
                {
                    "axis": "V",
                    "rule": "tier1_q07_partial_measures",
                    "value": tcfg["q7_yes_q8_or_q9_not_yes_delta"],
                    "source": None,
                    "fetched_at": None,
                }
            )

    if tier1_present and answers.get("q06") == "yes":
        v_running += tcfg["q6_yes_delta"]
        evidence.append({"axis": "V", "rule": "tier1_q06_yes", "value": tcfg["q6_yes_delta"], "source": None, "fetched_at": None})

    if tier1_present and answers.get("q10") == "yes":
        v_running += tcfg["q10_yes_delta"]
        evidence.append({"axis": "V", "rule": "tier1_q10_yes", "value": f"+{tcfg['q10_yes_delta']}", "source": None, "fetched_at": None})

    v_running = min(max(v_running, v_cfg["min"]), v_cfg["max"])

    if tier1_present and answers.get("q03") == "yes":
        v_final = tcfg["q3_yes_fixed_value"]
        evidence.append(
            {"axis": "V", "rule": "tier1_q03_yes_fixed", "value": f"V={v_final}（固定）", "source": None, "fetched_at": None}
        )
    elif tier1_present and answers.get("q03") == "no" and answers.get("q04") == "yes" and answers.get("q05") == "no":
        v_final = min(v_running, tcfg["q3_no_q4_yes_q5_no_cap"])
        evidence.append(
            {
                "axis": "V",
                "rule": "tier1_q03_no_q4_yes_q5_no_cap",
                "value": f"V=min(V,{tcfg['q3_no_q4_yes_q5_no_cap']})={v_final}",
                "source": None,
                "fetched_at": None,
            }
        )
    else:
        v_final = v_running

    return v_final, evidence


def _compute_i(
    feature: Feature, answers: dict[str, str], i_cfg: dict[str, Any], scores: dict[str, Any], meta: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    ctx = Context(features=feature.as_dict(), answers=answers, scores=scores, meta=meta)
    base = first_match_value(i_cfg["base_table"], ctx, default=i_cfg["default_value"])
    delta, applied = sum_deltas(i_cfg["additions"], ctx)
    total = min(max(base + delta, i_cfg["min"]), i_cfg["max"])
    evidence = [
        {
            "axis": "I",
            "rule": "usage_class_base",
            "value": f"usage_class={feature.usage_class} -> base I={base}",
            "source": feature.data_versions,
            "fetched_at": None,
        }
    ]
    for a in applied:
        evidence.append({"axis": "I", "rule": f"addition_{a['id']}", "value": a["label"], "source": None, "fetched_at": None})
    return total, evidence


def _compute_c(ctx: Context, c_cfg: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    total = 0
    applied_weights = []
    for w in c_cfg["weights"]:
        if evaluate_condition(w["condition"], ctx):
            total += w["weight"]
            applied_weights.append(w)
    deductions_applied = []
    for d in c_cfg["deductions"]:
        if evaluate_condition(d["condition"], ctx):
            total -= d["penalty"]
            deductions_applied.append(d)
    total = max(min(total, c_cfg["max"]), c_cfg["min"])
    evidence = [
        {"axis": "C", "rule": f"weight_{w['id']}", "value": w["weight"], "source": None, "fetched_at": None}
        for w in applied_weights
    ]
    for d in deductions_applied:
        evidence.append({"axis": "C", "rule": f"deduction_{d['id']}", "value": -d["penalty"], "source": None, "fetched_at": None})
    return total, evidence


def _compute_priority(
    P: int, I: int, C: int, priority_matrix_cfg: dict[str, Any], raise_cfg: dict[str, Any]
) -> tuple[str, bool]:
    base = priority_matrix_cfg["rows"][P][I]
    raised = False
    if C < raise_cfg["confidence_threshold"] and P >= raise_cfg["min_p"]:
        order = raise_cfg["order"]
        idx = order.index(base)
        if idx < len(order) - 1:
            base = order[idx + 1]
            raised = True
    label = base + (raise_cfg["suffix"] if raised else "")
    return label, raised


def _compute_missing_info(ctx: Context, rules_cfg: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    checks: list[str] = []
    for rule in rules_cfg:
        if evaluate_condition(rule["condition"], ctx):
            for m in rule["missing_info"]:
                if m not in missing:
                    missing.append(m)
            for c in rule["priority_checks"]:
                if c not in checks:
                    checks.append(c)
    return missing, checks


def assess(
    feature: Feature,
    answers: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
    measures_config: dict[str, Any] | None = None,
    computed_at: str | None = None,
) -> Assessment:
    """docs/03_スコアリング仕様.md に従い建物 1 件を評価する。

    answers はこの建物の Tier1 回答（q01..q12 -> yes/no/unknown）。未診断なら None。
    """
    if config is None:
        config = load_scoring_config()
    if measures_config is None:
        measures_config = load_measures_config()

    now = computed_at or _now_iso()
    as_of_year = int(now[:4])
    tier1_present = answers is not None
    norm_answers = _normalize_answers(answers)
    meta = {"tier1_present": tier1_present, "as_of_year": as_of_year}

    status = _determine_status(feature, config["status"])

    if status == "out_of_scope":
        return Assessment(
            building_id=feature.building_id,
            tier=1 if tier1_present else 0,
            score_version=config["score_version"],
            data_version=feature.data_versions,
            computed_at=now,
            status=status,
            H=None,
            V=None,
            I=None,
            P=None,
            C=None,
            priority=None,
            priority_raised_by_low_confidence=False,
            evidence=[],
            missing_info=[],
            priority_checks=[],
            measures=[],
        )

    c_ctx = Context(features=feature.as_dict(), answers=norm_answers, scores={}, meta=meta)
    C, c_evidence = _compute_c(c_ctx, config["c"])

    if status == "insufficient_data":
        H = None
        h_evidence = [
            {
                "axis": "H",
                "rule": "insufficient_data",
                "value": "内水・洪水データがなく、浸水実績・窪地フラグもないためH算出不能",
                "source": feature.data_versions,
                "fetched_at": None,
            }
        ]
    else:
        H, h_evidence = _compute_h(feature, config["h"], meta)

    scores: dict[str, Any] = {"H": H}
    V, v_evidence = _compute_v(feature, norm_answers, config["v"], scores, meta)
    scores["V"] = V

    I, i_evidence = _compute_i(feature, norm_answers, config["i"], scores, meta)
    scores["I"] = I
    scores["C"] = C

    if H is not None:
        P = config["p_matrix"]["rows"][H][V]
    else:
        P = None
    scores["P"] = P

    if P is not None:
        priority, raised = _compute_priority(P, I, C, config["priority_matrix"], config["priority_low_confidence_raise"])
    else:
        priority, raised = None, False

    full_ctx = Context(features=feature.as_dict(), answers=norm_answers, scores=scores, meta=meta)
    missing_info, priority_checks = _compute_missing_info(full_ctx, config["missing_info_rules"])
    if status == "insufficient_data":
        for item in ("内水浸水データ", "洪水浸水データ"):
            if item not in missing_info:
                missing_info.insert(0, item)

    measures = evaluate_measures(full_ctx, measures_config)

    evidence = h_evidence + v_evidence + i_evidence + c_evidence

    return Assessment(
        building_id=feature.building_id,
        tier=1 if tier1_present else 0,
        score_version=config["score_version"],
        data_version=feature.data_versions,
        computed_at=now,
        status=status,
        H=H,
        V=V,
        I=I,
        P=P,
        C=C,
        priority=priority,
        priority_raised_by_low_confidence=raised,
        evidence=evidence,
        missing_info=missing_info,
        priority_checks=priority_checks,
        measures=measures,
    )
