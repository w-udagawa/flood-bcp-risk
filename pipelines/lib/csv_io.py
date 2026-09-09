"""features.csv / features.jsonl 書き出しユーティリティ（標準ライブラリのみ）。

`config/features_schema.json` の規約に合わせて値を整形する:
  - CSV では null は空文字、boolean は "true"/"false" 文字列。
  - JSON Lines では null は JSON null、boolean は JSON true/false のまま。

`pipelines/60_export_features.py` から呼び出す想定。
"""

from __future__ import annotations

import csv
import json
from typing import Iterable, Sequence


def format_csv_value(value):
    """1 セル分の値を CSV 出力用の文字列に整形する。

    - None -> "" （空文字）
    - bool -> "true" / "false"
    - それ以外（str/int/float） -> str(value)
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def row_to_csv_row(row: dict, fieldnames: Sequence[str]) -> dict:
    """features_schema のフィールド順に整形した CSV 用の1行分 dict を返す。

    schema に存在しないキーは無視し、schema にあるが row に無いキーは
    空文字（欠損）として埋める。
    """
    return {name: format_csv_value(row.get(name)) for name in fieldnames}


def write_features_csv(rows: Iterable[dict], fieldnames: Sequence[str], path: str) -> int:
    """features.csv を書き出す。書き出した行数を返す。"""
    count = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row_to_csv_row(row, fieldnames))
            count += 1
    return count


def row_to_jsonl_row(row: dict, fieldnames: Sequence[str]) -> dict:
    """features_schema のフィールドのみを残した JSON Lines 用の1行分 dict を返す。

    値は Python のネイティブ型（None/bool/int/float/str）のまま保持する
    （CSV とは異なり文字列化しない）。
    """
    return {name: row.get(name) for name in fieldnames}


def write_features_jsonl(rows: Iterable[dict], fieldnames: Sequence[str], path: str) -> int:
    """features.jsonl（1行1レコードの JSON Lines）を書き出す。書き出した行数を返す。"""
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row_to_jsonl_row(row, fieldnames), ensure_ascii=False))
            f.write("\n")
            count += 1
    return count
