"""floodbcp CLI。

    python -m floodbcp assess --features <csv|jsonl> [--answers <csv>] --out <json> [--csv <csv>] [--config <json>]
    python -m floodbcp explain --features <csv|jsonl> --building-id <id> [--answers <csv>] [--config <json>]
    python -m floodbcp report --assessments <json> [--features <csv|jsonl>] --priority-list <csv> --facility-list <csv>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import SCORE_VERSION, __version__
from .features import SchemaError, load_features
from .measures import load_measures_config, measure_titles
from .questionnaire import QuestionnaireError, load_answers_csv
from .report import write_csv, write_facility_list_csv, write_json, write_priority_list_csv
from .scoring import Assessment, assess, load_scoring_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="floodbcp", description="洪水BCPリスク スコアリングエンジン CLI")
    parser.add_argument("--version", action="version", version=f"floodbcp {__version__} (score_version {SCORE_VERSION})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_assess = sub.add_parser("assess", help="特徴量ファイルを一括評価する")
    p_assess.add_argument("--features", required=True, help="features CSV または JSON Lines")
    p_assess.add_argument("--answers", help="Tier1 回答 CSV（任意）")
    p_assess.add_argument("--out", required=True, help="評価結果 JSON の出力先")
    p_assess.add_argument("--csv", help="評価結果 CSV の出力先（任意）")
    p_assess.add_argument("--config", help="スコアリング設定 JSON（既定: config/scoring_v0.1.0.json）")
    p_assess.add_argument("--measures-config", help="対策候補設定 JSON（既定: config/measures.json）")

    p_explain = sub.add_parser("explain", help="1棟をカルテ形式（人間向け）で表示する")
    p_explain.add_argument("--features", required=True, help="features CSV または JSON Lines")
    p_explain.add_argument("--building-id", required=True, help="対象building_id")
    p_explain.add_argument("--answers", help="Tier1 回答 CSV（任意）")
    p_explain.add_argument("--config", help="スコアリング設定 JSON（既定: config/scoring_v0.1.0.json）")
    p_explain.add_argument("--measures-config", help="対策候補設定 JSON（既定: config/measures.json）")

    p_report = sub.add_parser("report", help="評価結果からレポート（優先現地調査リスト・管理施設一覧）を出力する（FR-11）")
    p_report.add_argument("--assessments", required=True, help="assess --out で生成した評価結果 JSON")
    p_report.add_argument("--features", help="features CSV/JSON Lines（name/ward_code/usage_class 補完用、任意）")
    p_report.add_argument("--priority-list", required=True, dest="priority_list", help="優先現地調査リスト CSV の出力先")
    p_report.add_argument("--facility-list", required=True, dest="facility_list", help="管理施設一覧 CSV の出力先")

    return parser


def _run_assess(args: argparse.Namespace) -> int:
    try:
        features = load_features(args.features)
    except SchemaError as exc:
        print(f"features エラー: {exc}", file=sys.stderr)
        return 2

    answers_map: dict[str, dict[str, str]] = {}
    if args.answers:
        try:
            answers_map = load_answers_csv(args.answers)
        except QuestionnaireError as exc:
            print(f"answers エラー: {exc}", file=sys.stderr)
            return 2

    config = load_scoring_config(args.config) if args.config else load_scoring_config()
    measures_config = load_measures_config(args.measures_config) if args.measures_config else load_measures_config()

    results: list[Assessment] = []
    for feature in features:
        building_answers = answers_map.get(feature.building_id)
        results.append(assess(feature, answers=building_answers, config=config, measures_config=measures_config))

    write_json(results, args.out)
    if args.csv:
        write_csv(results, args.csv)

    counts: dict[str, int] = {}
    for r in results:
        key = r.priority or r.status
        counts[key] = counts.get(key, 0) + 1
    print(f"評価件数: {len(results)}  内訳: {counts}")
    return 0


def _format_evidence(evidence: list[dict[str, object]]) -> str:
    lines = []
    for e in evidence:
        src = e.get("source") or "-"
        lines.append(f"  [{e['axis']}] {e['rule']}: {e['value']}（出典: {src}）")
    return "\n".join(lines) if lines else "  （なし）"


def _run_explain(args: argparse.Namespace) -> int:
    try:
        features = load_features(args.features)
    except SchemaError as exc:
        print(f"features エラー: {exc}", file=sys.stderr)
        return 2

    target = next((f for f in features if f.building_id == args.building_id), None)
    if target is None:
        print(f"building_id {args.building_id!r} が features に見つかりません", file=sys.stderr)
        return 1

    answers_map: dict[str, dict[str, str]] = {}
    if args.answers:
        try:
            answers_map = load_answers_csv(args.answers)
        except QuestionnaireError as exc:
            print(f"answers エラー: {exc}", file=sys.stderr)
            return 2

    config = load_scoring_config(args.config) if args.config else load_scoring_config()
    measures_config = load_measures_config(args.measures_config) if args.measures_config else load_measures_config()
    titles = measure_titles(measures_config)

    result = assess(
        target,
        answers=answers_map.get(target.building_id),
        config=config,
        measures_config=measures_config,
    )

    print("=" * 60)
    print(f"建物カルテ: {target.building_id}（{target.name or '名称不明'}）")
    print("=" * 60)
    print(f"用途分類     : {target.usage_class or '不明'}")
    print(f"評価ステータス: {result.status}")
    print(f"score_version : {result.score_version}  computed_at: {result.computed_at}  tier: {result.tier}")
    print("-" * 60)
    print(f"H (ハザード)     : {result.H}")
    print(f"V (流入脆弱性)   : {result.V}")
    print(f"I (事業影響度)   : {result.I}")
    print(f"P (設備被災可能性): {result.P}")
    print(f"C (データ確信度) : {result.C}")
    print(f"優先度          : {result.priority}"
          + ("（確信度低下により1段階引き上げ）" if result.priority_raised_by_low_confidence else ""))
    print("-" * 60)
    print("根拠 (evidence):")
    print(_format_evidence(result.evidence))
    print("-" * 60)
    print("不足情報:")
    for m in result.missing_info:
        print(f"  - {m}")
    print("優先確認事項:")
    for c in result.priority_checks:
        print(f"  - {c}")
    print("-" * 60)
    print("対策候補:")
    for mid in result.measures:
        print(f"  - {mid}: {titles.get(mid, '(タイトル不明)')}")
    print("=" * 60)
    print("注記: 本評価は一次スクリーニングであり、安全性を保証するものではありません。")
    return 0


def _run_report(args: argparse.Namespace) -> int:
    try:
        with open(args.assessments, encoding="utf-8") as f:
            assessments = json.load(f)
    except OSError as exc:
        print(f"assessments エラー: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"assessments エラー: JSON として解釈できません: {exc}", file=sys.stderr)
        return 2
    if not isinstance(assessments, list):
        print("assessments エラー: JSON 配列（assess --out の出力形式）ではありません", file=sys.stderr)
        return 2

    features_by_id: dict[str, dict] = {}
    if args.features:
        try:
            features = load_features(args.features)
        except SchemaError as exc:
            print(f"features エラー: {exc}", file=sys.stderr)
            return 2
        features_by_id = {f.building_id: f.as_dict() for f in features}

    write_priority_list_csv(assessments, args.priority_list, features_by_id=features_by_id or None)
    write_facility_list_csv(assessments, args.facility_list, features_by_id=features_by_id or None)

    priority_count = sum(1 for a in assessments if isinstance(a, dict) and a.get("priority") in ("A", "A*", "B", "B*"))
    print(f"優先現地調査リスト: {priority_count} 件 -> {args.priority_list}")
    print(f"管理施設一覧: {len(assessments)} 件 -> {args.facility_list}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "assess":
        return _run_assess(args)
    if args.command == "explain":
        return _run_explain(args)
    if args.command == "report":
        return _run_report(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
