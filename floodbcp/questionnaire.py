"""Tier 1 簡易診断（12問）の回答読み込み。

docs/03_スコアリング仕様.md 第6章に対応。
CSV 列: building_id, q01, q02, ..., q12。値は yes / no / unknown（空欄は unknown 扱い）。
"""
from __future__ import annotations

import csv
from pathlib import Path

QUESTION_IDS = tuple(f"q{i:02d}" for i in range(1, 13))
VALID_ANSWERS = {"yes", "no", "unknown"}


class QuestionnaireError(ValueError):
    pass


def _normalize_answer(raw: str, *, row_no: int, question: str) -> str:
    value = (raw or "").strip().lower()
    if value == "":
        return "unknown"
    if value not in VALID_ANSWERS:
        raise QuestionnaireError(
            f"row {row_no}: {question} の値は yes/no/unknown である必要があります: {raw!r}"
        )
    return value


def load_answers_csv(path: Path | str) -> dict[str, dict[str, str]]:
    """building_id -> {"q01": "yes"|"no"|"unknown", ...} の辞書を返す。

    未回答（欠落した Q）は "unknown" とする。
    """
    answers: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "building_id" not in reader.fieldnames:
            raise QuestionnaireError("answers CSV に building_id 列がありません")
        for row_no, row in enumerate(reader, start=2):
            building_id = (row.get("building_id") or "").strip()
            if not building_id:
                raise QuestionnaireError(f"row {row_no}: building_id が空です")
            record = {
                q: _normalize_answer(row.get(q, ""), row_no=row_no, question=q)
                for q in QUESTION_IDS
            }
            answers[building_id] = record
    return answers
