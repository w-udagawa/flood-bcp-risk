#!/usr/bin/env python3
"""dbf_inspect.py の JSON 出力と depth_class_tables.json の写像表を突き合わせる。

用途（docs/tasks/TASK-006_M1検証ツールキット.md）：
  - V-02: 東京都浸水予想区域図（他、A31/A51/A49 も同じ仕組みで使える）の
    浸水深階級コード・ラベルの写像表更新

`tools/verify/dbf_inspect.py --json-out <file>` の出力（属性テーブルの
フィールドごとの top_values を含む）と、`pipelines/config/depth_class_tables.json`
の `sources.<source>.class_codes`（コード -> [min_m, max_m]）を比較し、

  - 実データに現れたが写像表に無いコード／ラベル（unmapped_in_data）
  - 写像表にはあるが実データには現れなかったコード（unused_in_table）

を報告する。判定は文字列の完全一致で行う（コードが "1" のような数値文字列
でも、ラベル文字列（例: "0.1m未満"）でも、指定した --field の値をそのまま
比較する）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

_DEFAULT_TABLES_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "pipelines",
        "config",
        "depth_class_tables.json",
    )
)


class CheckError(RuntimeError):
    pass


def load_dbf_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tables(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_field(dbf_data: dict, field_name: str) -> dict:
    for f in dbf_data.get("fields", []):
        if f["name"] == field_name:
            return f
    available = [f["name"] for f in dbf_data.get("fields", [])]
    raise CheckError(
        f"フィールド '{field_name}' が dbf_inspect の JSON に見つかりません"
        f"（利用可能なフィールド: {available}）"
    )


def get_source_entry(tables: dict, source: str) -> dict:
    sources = tables.get("sources", {})
    if source not in sources:
        raise CheckError(
            f"source '{source}' が写像表に見つかりません（利用可能: {list(sources.keys())}）"
        )
    return sources[source]


def compare(field_stats: dict, source_entry: dict) -> dict:
    data_values = {v["value"] for v in field_stats.get("top_values", [])}
    data_value_counts = {v["value"]: v["count"] for v in field_stats.get("top_values", [])}
    table_codes = set(str(c) for c in source_entry.get("class_codes", {}).keys())

    unmapped_in_data = sorted(data_values - table_codes)
    unused_in_table = sorted(table_codes - data_values)

    return {
        "field": field_stats["name"],
        "data_unique_count": field_stats.get("unique_count"),
        "data_top_values_examined": len(data_values),
        "note_if_truncated": (
            "top_values は dbf_inspect の --top-n 件に切り詰められているため、"
            "unique_count がこの件数より大きい場合、表示されていない値が"
            "unmapped として検出されていない可能性がある。--top-n を増やして"
            "再実行することを推奨する。"
            if field_stats.get("unique_count", 0) > len(data_values)
            else None
        ),
        "unmapped_in_data": [
            {"value": v, "count": data_value_counts.get(v)} for v in unmapped_in_data
        ],
        "unused_in_table": unused_in_table,
        "table_verified_flag": source_entry.get("verified"),
        "table_source_url": source_entry.get("source_url"),
    }


def render_text_report(result: dict) -> str:
    lines = []
    lines.append(f"フィールド: {result['field']}")
    lines.append(
        f"写像表の verified フラグ: {result['table_verified_flag']}  "
        f"source_url: {result['table_source_url']}"
    )
    if result["note_if_truncated"]:
        lines.append(f"[注意] {result['note_if_truncated']}")
    lines.append("")
    if result["unmapped_in_data"]:
        lines.append("写像表に無い値（実データに出現）:")
        for item in result["unmapped_in_data"]:
            lines.append(f"  - {item['value']!r}（{item['count']} 件）")
    else:
        lines.append("写像表に無い値: なし（実データの上位値はすべて写像表でカバーされています）")
    lines.append("")
    if result["unused_in_table"]:
        lines.append("写像表にあるが実データ上位に出現しなかった値:")
        for v in result["unused_in_table"]:
            lines.append(f"  - {v!r}")
    else:
        lines.append("写像表にあるが未出現の値: なし")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "dbf_inspect.py の JSON 出力と pipelines/config/depth_class_tables.json "
            "を突き合わせ、実データに現れた階級コード／ラベルのうち写像表に無いものを"
            "列挙する。"
        )
    )
    parser.add_argument(
        "dbf_json",
        help="dbf_inspect.py --json-out で出力した JSON ファイルのパス",
    )
    parser.add_argument(
        "--field",
        required=True,
        help="浸水深階級コード（またはラベル）が入っているフィールド名",
    )
    parser.add_argument(
        "--source",
        required=True,
        help=(
            "depth_class_tables.json の sources 内のキー"
            "（例: tokyo_inundation_map, ksj_a31, ksj_a51, ksj_a49, plateau_risk_attribute）"
        ),
    )
    parser.add_argument(
        "--tables",
        default=_DEFAULT_TABLES_PATH,
        help=f"depth_class_tables.json のパス（既定: {_DEFAULT_TABLES_PATH}）",
    )
    parser.add_argument("--json-out", default=None, help="結果を JSON で書き出すファイルパス")
    parser.add_argument("--quiet", action="store_true", help="標準出力へのテキストレポートを抑制する")
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        dbf_data = load_dbf_json(args.dbf_json)
        tables = load_tables(args.tables)
        field_stats = find_field(dbf_data, args.field)
        source_entry = get_source_entry(tables, args.source)
    except (CheckError, FileNotFoundError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"エラー: {exc}\n")
        return 1

    result = compare(field_stats, source_entry)

    if not args.quiet:
        print(render_text_report(result))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"\nJSON を書き出しました: {args.json_out}")

    # unmapped がある場合、判定に使える終了コードとして 2 を返す
    # （V-02 の写像表更新が必要というシグナル。--json-out 等の自動処理向け）。
    if result["unmapped_in_data"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
