"""対策候補（措置メニュー）の評価。

docs/03_スコアリング仕様.md 第13章に対応。対策 ID と提示条件は
config/measures.json のみが持ち、ここではその条件を汎用評価するだけ。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .rules import Context, evaluate_condition

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent
DEFAULT_MEASURES_PATH = _REPO_ROOT / "config" / "measures.json"


def load_measures_config(path: Path | str = DEFAULT_MEASURES_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_measures(ctx: Context, measures_config: dict[str, Any]) -> list[str]:
    """条件が真になった対策 ID のリストを、config の記載順で返す。"""
    result = []
    for measure in measures_config["measures"]:
        if evaluate_condition(measure["condition"], ctx):
            result.append(measure["id"])
    return result


def measure_titles(measures_config: dict[str, Any]) -> dict[str, str]:
    return {m["id"]: m["title"] for m in measures_config["measures"]}
