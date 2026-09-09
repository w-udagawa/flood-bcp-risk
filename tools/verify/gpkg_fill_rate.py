#!/usr/bin/env python3
"""GeoPackage（SQLite）の属性収録率を標準ライブラリの sqlite3 のみで集計する。

用途（docs/tasks/TASK-006_M1検証ツールキット.md）：
  - V-01: PLATEAU 建物モデル（GIS Converter で変換した GeoPackage）の
    地下階数・浸水リスク属性等の収録率

GeoPackage は仕様上ふつうの SQLite ファイルであり、`gpkg_contents` テーブル
にレイヤ（テーブル）一覧が入っている。ジオメトリ列を読む必要はなく、属性
列の非 null 率等を集計するだけなので geopandas 等は不要。

列名は PLATEAU GIS Converter の出力バージョンや変換設定に依存して揺れる
可能性があるため、`--columns-like` は部分一致（大文字小文字を区別しない）
で列を探す。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from typing import Optional

# PLATEAU の災害リスク・地下階数まわりで関心の高い列名（部分一致キーワード）。
# 実列名は GIS Converter の出力に依存するため、これらはあくまで「優先表示」
# のためのヒントであり、網羅的な列名確定を意味しない。
DEFAULT_COLUMNS_LIKE = [
    "storeysBelowGround",
    "storeysAboveGround",
    "usage",
    "yearOfConstruction",
    "measuredHeight",
    "totalFloorArea",
    "buildingFootprintArea",
    "Flooding",
    "HighTide",
    "Inland",
    "River",
    "depth",
    "rank",
]

DEFAULT_LAYER_LIKE = ["bldg", "Building"]


class GpkgError(RuntimeError):
    pass


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def list_layers(conn: sqlite3.Connection) -> list[dict]:
    if not _table_exists(conn, "gpkg_contents"):
        raise GpkgError(
            "gpkg_contents テーブルが見つかりません。GeoPackage 仕様に準拠した"
            "ファイルではない可能性があります。"
        )
    cur = conn.execute(
        "SELECT table_name, data_type, identifier, description FROM gpkg_contents"
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def select_target_layers(
    layers: list[dict], layer_like: list[str], explicit_layer: Optional[str]
) -> list[str]:
    table_names = [l["table_name"] for l in layers]
    if explicit_layer:
        if explicit_layer not in table_names:
            raise GpkgError(
                f"指定レイヤ '{explicit_layer}' は gpkg_contents に存在しません"
                f"（存在するレイヤ: {table_names}）"
            )
        return [explicit_layer]
    matched = [
        t for t in table_names if any(pat.lower() in t.lower() for pat in layer_like)
    ]
    return matched


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in cur.fetchall()]


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def analyze_layer(conn: sqlite3.Connection, table: str, columns_like: list[str]) -> dict:
    columns = get_columns(conn, table)
    cur = conn.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}")
    row_count = cur.fetchone()[0]

    col_stats = []
    for col in columns:
        qcol = _quote_ident(col)
        qtable = _quote_ident(table)
        cur = conn.execute(
            f"SELECT "
            f"COUNT(*) AS total, "
            f"SUM(CASE WHEN {qcol} IS NOT NULL THEN 1 ELSE 0 END) AS non_null, "
            f"SUM(CASE WHEN {qcol} IS NOT NULL AND CAST({qcol} AS TEXT) != '' THEN 1 ELSE 0 END) AS non_empty, "
            f"COUNT(DISTINCT {qcol}) AS unique_count "
            f"FROM {qtable}"
        )
        total, non_null, non_empty, unique_count = cur.fetchone()
        total = total or 0
        non_null = non_null or 0
        non_empty = non_empty or 0
        unique_count = unique_count or 0
        is_priority = any(pat.lower() in col.lower() for pat in columns_like)
        col_stats.append(
            {
                "column": col,
                "priority": is_priority,
                "total_count": total,
                "non_null_count": non_null,
                "non_null_rate": round(non_null / total, 4) if total else 0.0,
                "non_empty_count": non_empty,
                "non_empty_rate": round(non_empty / total, 4) if total else 0.0,
                "unique_count": unique_count,
            }
        )

    # 優先列を先頭に、それ以外は列定義順のまま。
    col_stats.sort(key=lambda c: (not c["priority"],))
    return {
        "table": table,
        "row_count": row_count,
        "columns": col_stats,
    }


def render_text_report(layers: list[dict], analyses: list[dict]) -> str:
    lines = []
    lines.append("=== gpkg_contents に登録されているレイヤ一覧 ===")
    for l in layers:
        lines.append(
            f"- {l['table_name']}  data_type={l['data_type']}  "
            f"identifier={l.get('identifier')}"
        )
    lines.append("")
    for a in analyses:
        lines.append(f"=== レイヤ: {a['table']}（{a['row_count']} 行） ===")
        for c in a["columns"]:
            mark = "*" if c["priority"] else " "
            lines.append(
                f"{mark} {c['column']}  非null率={c['non_null_rate']:.1%}"
                f"（{c['non_null_count']}/{c['total_count']}）  "
                f"非空文字率={c['non_empty_rate']:.1%}  "
                f"ユニーク数={c['unique_count']}"
            )
        lines.append("")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "GeoPackage（SQLite）を sqlite3 のみで開き、指定レイヤの属性収録率"
            "（非null率・非空文字率・ユニーク数）を集計する。"
        )
    )
    parser.add_argument("path", help="GeoPackage (.gpkg) ファイルのパス")
    parser.add_argument(
        "--layer",
        default=None,
        help="集計対象レイヤ名を明示指定する（省略時は --layer-like で自動選択）",
    )
    parser.add_argument(
        "--layer-like",
        default=",".join(DEFAULT_LAYER_LIKE),
        help=(
            "レイヤ名の部分一致キーワード（カンマ区切り、既定: "
            f"{','.join(DEFAULT_LAYER_LIKE)}）"
        ),
    )
    parser.add_argument(
        "--columns-like",
        default=",".join(DEFAULT_COLUMNS_LIKE),
        help="優先表示する列名の部分一致キーワード（カンマ区切り）",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="集計結果を JSON で書き出すファイルパス",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="標準出力へのテキストレポートを抑制する",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    layer_like = [s for s in args.layer_like.split(",") if s]
    columns_like = [s for s in args.columns_like.split(",") if s]

    try:
        conn = sqlite3.connect(f"file:{args.path}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        sys.stderr.write(f"エラー: ファイルを開けません: {exc}\n")
        return 1

    try:
        layers = list_layers(conn)
        targets = select_target_layers(layers, layer_like, args.layer)
        if not targets:
            sys.stderr.write(
                f"エラー: 条件に合うレイヤが見つかりません（layer-like={layer_like}）。"
                f"gpkg_contents のレイヤ: {[l['table_name'] for l in layers]}\n"
            )
            return 1
        analyses = [analyze_layer(conn, t, columns_like) for t in targets]
    except (GpkgError, sqlite3.OperationalError) as exc:
        sys.stderr.write(f"エラー: {exc}\n")
        return 1
    finally:
        conn.close()

    if not args.quiet:
        print(render_text_report(layers, analyses))

    if args.json_out:
        payload = {
            "source_path": args.path,
            "layers": layers,
            "analyses": analyses,
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if not args.quiet:
            print(f"\nJSON を書き出しました: {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
