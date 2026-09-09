"""Assessment のシリアライズ（JSON / CSV）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .scoring import Assessment

CSV_FIELDS = [
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
    "missing_info",
    "priority_checks",
    "measures",
    "evidence",
]


def write_json(assessments: Iterable[Assessment], path: Path | str) -> None:
    payload = [a.as_dict() for a in assessments]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _flatten_for_csv(a: Assessment) -> dict[str, object]:
    d = a.as_dict()
    row = {k: d[k] for k in CSV_FIELDS if k not in ("missing_info", "priority_checks", "measures", "evidence")}
    row["missing_info"] = json.dumps(d["missing_info"], ensure_ascii=False)
    row["priority_checks"] = json.dumps(d["priority_checks"], ensure_ascii=False)
    row["measures"] = ";".join(d["measures"])
    row["evidence"] = json.dumps(d["evidence"], ensure_ascii=False)
    return row


def write_csv(assessments: Iterable[Assessment], path: Path | str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for a in assessments:
            writer.writerow(_flatten_for_csv(a))


# ---------------------------------------------------------------------------
# FR-11 レポート出力（優先現地調査リスト・管理施設一覧）
#
# 以下の write_priority_list_csv() / write_facility_list_csv() は、Assessment
# オブジェクトではなく Assessment.as_dict() と同じキーを持つ dict（docs/03 第11章の
# スキーマ）を受け取る。`python -m floodbcp report` は `assess --out` が書き出した
# JSON（= as_dict() のリスト）をそのまま読み込んで渡すのが主な用途であり、
# floodbcp/scoring.py の Assessment 型に依存させないことで report.py 単体でも
# 完結させるための設計上の選択。in-process で Assessment のリストを渡す場合は
# `[a.as_dict() for a in assessments]` を渡せばよい。
# ---------------------------------------------------------------------------

# 優先度順（docs/03_スコアリング仕様.md 第9章の確信度ルールによる "*" 付きを含む）。
PRIORITY_SORT_ORDER = ["A", "A*", "B", "B*"]

PRIORITY_LIST_FIELDS = [
    "building_id",
    "name",
    "usage_class",
    "priority",
    "P",
    "H",
    "V",
    "I",
    "C",
    "status",
    "main_factors",
    "priority_checks",
    "measures",
]

FACILITY_LIST_FIELDS = [
    "building_id",
    "name",
    "ward_code",
    "usage_class",
    "priority",
    "P",
    "H",
    "V",
    "I",
    "C",
    "status",
    "tier",
    "computed_at",
]

# H/V/I の evidence rule 名 -> 日本語の短い要因説明。
# config/scoring_v0.1.0.json の corrections/adjustments/additions の id から
# 機械的に組み立てられる rule 名（"correction_<id>" 等、floodbcp/scoring.py 参照）に
# 対応させている。config の数値・条件そのものは変更しない（表示用の翻訳のみ）。
_RULE_LABELS_JA: dict[tuple[str, str], str] = {
    ("H", "depth_rep"): "浸水想定深による基礎等級",
    ("H", "provisional_no_depth_data"): "浸水想定データなし（実績/窪地により暫定等級）",
    ("H", "zero_grade_history_override"): "区域外相当だが浸水実績あり",
    ("H", "insufficient_data"): "浸水想定データ不足のためH算出不能",
    ("H", "correction_history"): "浸水実績あり（補正）",
    ("H", "correction_depression_or_below_road"): "窪地または道路より低い立地（補正）",
    ("H", "correction_landform"): "浸水しやすい地形分類（補正）",
    ("V", "storeys_below"): "地下階数",
    ("V", "storeys_below_estimated"): "地下階不明のため用途分類から推定",
    ("V", "adjustment_electric_room_likely"): "延床面積・階数から電気室等が低層にある可能性",
    ("V", "adjustment_below_road"): "道路面より低い立地",
    ("V", "adjustment_post_guideline_design"): "新耐水基準以降の建築年",
    ("V", "adjustment_station_usage"): "駅施設であること",
    ("V", "tier1_q01_no_reset_base"): "簡易診断Q1=いいえ（地下に重要設備なし）",
    ("V", "tier1_q02_yes"): "簡易診断Q2=はい（浸水しやすい開口部あり）",
    ("V", "tier1_q03_yes_fixed"): "簡易診断Q3=はい（重要設備が浸水想定より低い）",
    ("V", "tier1_q03_no_q4_yes_q5_no_cap"): "簡易診断の回答により脆弱性を抑制",
    ("V", "tier1_q06_yes"): "簡易診断Q6=はい（排水ポンプに非常電源あり）",
    ("V", "tier1_q07_full_measures"): "簡易診断Q7〜Q9=はい（止水対策が整っている）",
    ("V", "tier1_q07_partial_measures"): "簡易診断Q7=はいだが対策が一部のみ",
    ("V", "tier1_q10_yes"): "簡易診断Q10=はい（単一系統に依存）",
    ("I", "usage_class_base"): "用途分類による基礎影響度",
    ("I", "addition_no_alt_facility_nearby"): "近隣に代替施設なし",
    ("I", "addition_q12_history"): "簡易診断Q12=はい（重大な事業影響の実績あり）",
    ("I", "addition_q10_single_system"): "簡易診断Q10=はい（系統構成が単一）",
}


def _main_factor_label(entry: dict[str, Any]) -> str:
    axis = entry.get("axis")
    rule = entry.get("rule")
    label = _RULE_LABELS_JA.get((axis, rule)) or f"{axis}要因（{rule}）"
    value = entry.get("value")
    return f"{axis}:{label}（{value}）" if value not in (None, "") else f"{axis}:{label}"


def main_factors_ja(evidence: list[dict[str, Any]] | None) -> str:
    """evidence（Assessment.evidence）から H/V/I の主要因を日本語で最大3件、
    「;」区切りの文字列にする。各軸（H/V/I）につき最初に記録された evidence
    （= floodbcp/scoring.py が最初に積む、その軸の基礎等級を決めた根拠）を
    「主要因」として採用する。軸は最大3つ（H/V/I）しかないため、この選び方で
    自然に上限3件になる。
    """
    if not evidence:
        return ""
    parts = []
    for axis in ("H", "V", "I"):
        entry = next((e for e in evidence if e.get("axis") == axis), None)
        if entry is None:
            continue
        parts.append(_main_factor_label(entry))
    return ";".join(parts[:3])


def _lookup(features_by_id: dict[str, dict[str, Any]] | None, building_id: str, key: str) -> Any:
    if not features_by_id:
        return ""
    feat = features_by_id.get(building_id)
    if not feat:
        return ""
    value = feat.get(key)
    return value if value is not None else ""


def _priority_list_row(a: dict[str, Any], features_by_id: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    building_id = a["building_id"]
    return {
        "building_id": building_id,
        "name": _lookup(features_by_id, building_id, "name"),
        "usage_class": _lookup(features_by_id, building_id, "usage_class"),
        "priority": a.get("priority"),
        "P": a.get("P"),
        "H": a.get("H"),
        "V": a.get("V"),
        "I": a.get("I"),
        "C": a.get("C"),
        "status": a.get("status"),
        "main_factors": main_factors_ja(a.get("evidence")),
        "priority_checks": ";".join(a.get("priority_checks") or []),
        "measures": ";".join(a.get("measures") or []),
    }


def write_priority_list_csv(
    assessments: Iterable[dict[str, Any]],
    path: Path | str,
    features_by_id: dict[str, dict[str, Any]] | None = None,
) -> None:
    """優先現地調査リスト（FR-11）を CSV に書き出す。

    優先度 A/A*/B/B* の建物のみを対象に、優先度順（A -> A* -> B -> B*）->
    P 降順 -> C 昇順で並べる。`assessments` は Assessment.as_dict() と同じ
    キーを持つ dict の列（`assess --out` が書き出す JSON をそのまま読み込んだもの）。
    `features_by_id`（building_id -> Feature.as_dict()）を渡すと name / usage_class を
    補完する。省略時は空欄になる。
    """
    rows = [a for a in assessments if a.get("priority") in PRIORITY_SORT_ORDER]
    rows.sort(key=lambda a: (PRIORITY_SORT_ORDER.index(a["priority"]), -(a.get("P") or 0), a.get("C") if a.get("C") is not None else 0))

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PRIORITY_LIST_FIELDS)
        writer.writeheader()
        for a in rows:
            writer.writerow(_priority_list_row(a, features_by_id))


def _facility_list_row(a: dict[str, Any], features_by_id: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    building_id = a["building_id"]
    return {
        "building_id": building_id,
        "name": _lookup(features_by_id, building_id, "name"),
        "ward_code": _lookup(features_by_id, building_id, "ward_code"),
        "usage_class": _lookup(features_by_id, building_id, "usage_class"),
        "priority": a.get("priority"),
        "P": a.get("P"),
        "H": a.get("H"),
        "V": a.get("V"),
        "I": a.get("I"),
        "C": a.get("C"),
        "status": a.get("status"),
        "tier": a.get("tier"),
        "computed_at": a.get("computed_at"),
    }


def write_facility_list_csv(
    assessments: Iterable[dict[str, Any]],
    path: Path | str,
    features_by_id: dict[str, dict[str, Any]] | None = None,
) -> None:
    """管理施設一覧（FR-11）を CSV に書き出す。全建物（status に関わらず）を、
    渡された順（通常は features ファイルの記載順）のまま書き出す。
    """
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FACILITY_LIST_FIELDS)
        writer.writeheader()
        for a in assessments:
            writer.writerow(_facility_list_row(a, features_by_id))
