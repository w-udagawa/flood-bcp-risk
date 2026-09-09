"""汎用の条件式評価エンジン。

config/scoring_v0.1.0.json と config/measures.json に置かれた
「条件（condition）」ツリーを、外から渡されたコンテキスト（Context）に対して
評価する。分岐ロジック自体はここに置くが、閾値・マトリクス・重み・対策条件の
"数値" はすべて JSON 側にある（floodbcp にハードコードしない）。

条件ツリーの形：
  組み合わせ:
    {"all": [cond, cond, ...]}   すべて真
    {"any": [cond, cond, ...]}   いずれか真
    {"not": cond}                 否定
  末端（leaf）:
    {"path": "features.rel_elev_m", "op": "lte", "value": -0.3}
    {"op": "always"}                         常に真
    {"op": "tier1_answered_count_gte", "value": 7}
    {"op": "inland_class_width_gte", "value": 2.5}
    {"op": "hazard_age_gt_years", "value": 10}

path の先頭セグメントは Context のバケット名（features / answers / scores / meta）、
残りはそのバケット内のキー名。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Context:
    """条件評価に使う値の入れ物。"""

    features: dict[str, Any] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)
    scores: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def get_path(self, path: str) -> Any:
        bucket_name, _, key = path.partition(".")
        bucket = getattr(self, bucket_name, None)
        if bucket is None:
            raise ValueError(f"unknown context bucket in path: {path!r}")
        if bucket_name == "answers":
            # 未回答（Tier1 なし）は unknown 扱い。
            return bucket.get(key, "unknown")
        return bucket.get(key)


def _cmp(op: str, left: Any, right: Any) -> bool:
    if op in ("gte", "lte", "gt", "lt"):
        if left is None:
            return False
        if op == "gte":
            return left >= right
        if op == "lte":
            return left <= right
        if op == "gt":
            return left > right
        if op == "lt":
            return left < right
    raise ValueError(f"unknown comparison op: {op!r}")


def evaluate_condition(condition: dict[str, Any], ctx: Context) -> bool:
    if "all" in condition:
        return all(evaluate_condition(c, ctx) for c in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(c, ctx) for c in condition["any"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], ctx)

    op = condition["op"]

    if op == "always":
        return True

    if op == "tier1_answered_count_gte":
        threshold = condition["value"]
        count = sum(
            1
            for q in ("q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08", "q09", "q10")
            if ctx.answers.get(q, "unknown") != "unknown"
        )
        return count >= threshold

    if op == "inland_class_width_gte":
        threshold = condition["value"]
        lo = ctx.features.get("inland_depth_min_m")
        hi = ctx.features.get("inland_depth_max_m")
        if lo is None or hi is None:
            return False
        return (hi - lo) >= threshold

    if op == "hazard_age_gt_years":
        threshold = condition["value"]
        year = ctx.features.get("hazard_source_year")
        as_of_year = ctx.meta.get("as_of_year")
        if year is None or as_of_year is None:
            return False
        return (as_of_year - year) > threshold

    # path 付きの末端条件。
    value = ctx.get_path(condition["path"]) if "path" in condition else None

    if op == "is_true":
        return value is True
    if op == "is_false":
        return value is False
    if op == "not_null":
        return value is not None
    if op == "is_null":
        return value is None
    if op == "eq":
        return value == condition["value"]
    if op == "ne":
        return value != condition["value"]
    if op == "in":
        return value in condition["value"]
    if op == "not_in":
        return value not in condition["value"]
    if op in ("gte", "lte", "gt", "lt"):
        return _cmp(op, value, condition["value"])

    raise ValueError(f"unknown condition op: {op!r}")


def first_match_value(table: list[dict[str, Any]], ctx: Context, default: Any = None) -> Any:
    """[{"condition": ..., "value": ...}, ...] を先頭から評価し、最初に真になった value を返す。"""
    for row in table:
        if evaluate_condition(row["condition"], ctx):
            return row["value"]
    return default


def sum_deltas(adjustments: list[dict[str, Any]], ctx: Context) -> tuple[int, list[dict[str, Any]]]:
    """[{"id","label","delta","condition"}, ...] のうち条件が真のものを合算し、
    (合計デルタ, 適用された補正のリスト) を返す。
    """
    total = 0
    applied = []
    for adj in adjustments:
        if evaluate_condition(adj["condition"], ctx):
            total += adj["delta"]
            applied.append(adj)
    return total, applied
