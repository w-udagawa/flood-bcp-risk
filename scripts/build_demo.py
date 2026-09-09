#!/usr/bin/env python3
"""scripts/build_demo.py（TASK-007）

`data/samples/` の架空データに対して floodbcp（評価エンジン）を実行し、
`web/data/` 配下のデモ用データを常に floodbcp の実出力・`config/` の設定と
整合させた状態で生成し直す。

    python3 scripts/build_demo.py

既定では `data/samples/features_sample.csv` / `answers_sample.csv` を入力に、
以下の3ファイルを上書き生成する。

- `web/data/assessments_sample.json`：`floodbcp.assess()` の実出力
  （docs/03_スコアリング仕様.md 第11章のスキーマ）。
- `web/data/buildings_sample.geojson`：サンプル建物ごとに、building_id から
  決定的にハッシュシードした乱数で生成した矩形ポリゴン（中心は自由が丘駅周辺、
  35.6075N, 139.6690E の半径 600m 程度）。プロパティは building_id, name,
  usage_class, ward_code, storeys_below, total_floor_area_m2 のみ
  （web/lib/join.js が参照するプロパティ名は変更しない）。
- `web/data/measures.json`：`config/measures.json`（対策候補の正本）から変換。
  二重管理をやめ、`config/measures.json` を唯一の情報源にする。

生成後、`node --test 'web/tests/*.test.js'` を実行して結果を表示する
（node が見つからない場合はスキップ表示のみで失敗にはしない）。

Python 標準ライブラリのみで動作する（floodbcp 本体と同じ制約、NFR-07）。
サンプルは全て架空であり、実在の建物・施設・住所とは一切関係ない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    # `python3 scripts/build_demo.py` のように直接実行された場合でも
    # floodbcp をリポジトリルートから import できるようにする。
    sys.path.insert(0, str(REPO_ROOT))

from floodbcp.features import Feature, load_features  # noqa: E402
from floodbcp.measures import load_measures_config  # noqa: E402
from floodbcp.questionnaire import load_answers_csv  # noqa: E402
from floodbcp.report import write_json  # noqa: E402
from floodbcp.scoring import assess, load_scoring_config  # noqa: E402

DEFAULT_FEATURES_CSV = REPO_ROOT / "data" / "samples" / "features_sample.csv"
DEFAULT_ANSWERS_CSV = REPO_ROOT / "data" / "samples" / "answers_sample.csv"
DEFAULT_MEASURES_CONFIG = REPO_ROOT / "config" / "measures.json"
DEFAULT_ASSESSMENTS_OUT = REPO_ROOT / "web" / "data" / "assessments_sample.json"
DEFAULT_BUILDINGS_OUT = REPO_ROOT / "web" / "data" / "buildings_sample.geojson"
DEFAULT_MEASURES_OUT = REPO_ROOT / "web" / "data" / "measures.json"

# 生成結果を実行時刻に依存させない（決定的にする）ための固定 computed_at。
# docs/03_スコアリング仕様.md 第11章の computed_at はスコア算出日時だが、
# デモ用サンプルは常にこの日時で固定し、再実行しても同一の JSON になるようにする。
FIXED_COMPUTED_AT = "2026-09-09T00:00:00Z"

# サンプル建物ポリゴンの生成中心（自由が丘駅周辺のおおよその座標、架空データ）と半径。
CENTER_LAT = 35.6075
CENTER_LON = 139.6690
RADIUS_M = 600.0
_LAT_M_PER_DEG = 111_320.0


# ---------------------------------------------------------------------------
# buildings_sample.geojson: building_id から決定的にハッシュシードした乱数で
# 矩形ポリゴンを生成する。
# ---------------------------------------------------------------------------


def _rng_for(building_id: str) -> random.Random:
    digest = hashlib.sha256(building_id.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    return random.Random(seed)


def _offset_to_latlon(center_lat: float, center_lon: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    lat = center_lat + dy_m / _LAT_M_PER_DEG
    lon_m_per_deg = _LAT_M_PER_DEG * math.cos(math.radians(center_lat))
    lon = center_lon + dx_m / lon_m_per_deg
    return lat, lon


def _rectangle_ring(center_lat: float, center_lon: float, half_w_m: float, half_d_m: float) -> list[list[float]]:
    # 反時計回り（GeoJSON の外環の向きの慣例）：左下 -> 右下 -> 右上 -> 左上 -> 左下
    corners_m = [(-half_w_m, -half_d_m), (half_w_m, -half_d_m), (half_w_m, half_d_m), (-half_w_m, half_d_m)]
    ring = [
        [round(lon, 7), round(lat, 7)]
        for lat, lon in (_offset_to_latlon(center_lat, center_lon, dx, dy) for dx, dy in corners_m)
    ]
    ring.append(ring[0])
    return ring


def _building_polygon(building_id: str, footprint_area_m2: float | None) -> dict[str, Any]:
    rng = _rng_for(building_id)
    # 中心から半径 RADIUS_M 以内に面積一様分布（r = R * sqrt(u)）で建物中心を配置する。
    r = RADIUS_M * math.sqrt(rng.random())
    theta = 2 * math.pi * rng.random()
    dx, dy = r * math.cos(theta), r * math.sin(theta)
    center_lat, center_lon = _offset_to_latlon(CENTER_LAT, CENTER_LON, dx, dy)

    side = math.sqrt(footprint_area_m2) if footprint_area_m2 and footprint_area_m2 > 0 else 15.0
    side = min(max(side, 8.0), 60.0)
    aspect = 0.6 + rng.random() * 0.8  # 0.6〜1.4（決定的）。面積は side**2 のまま変わらない。
    half_w = (side * aspect) / 2
    half_d = (side / aspect) / 2

    return {"type": "Polygon", "coordinates": [_rectangle_ring(center_lat, center_lon, half_w, half_d)]}


def _building_display_name(feature: Feature) -> str:
    # web/tests/join.test.js（編集不可）は、サンプル建物名に架空マーカー
    # "サンプル" が含まれることを検証している。data/samples/ 側は
    # "架空:" 接頭辞を使っているため、ここでビューア表示用の名称として
    # 明示的に "（サンプルデータ）" を付す。
    base = feature.name or feature.building_id
    return f"{base}（サンプルデータ）"


def build_buildings_geojson(features: list[Feature]) -> dict[str, Any]:
    out_features = []
    for f in features:
        properties = {
            "building_id": f.building_id,
            "name": _building_display_name(f),
            "usage_class": f.usage_class,
            "ward_code": f.ward_code,
            "storeys_below": f.storeys_below,
            "total_floor_area_m2": f.total_floor_area_m2,
        }
        out_features.append(
            {
                "type": "Feature",
                "geometry": _building_polygon(f.building_id, f.footprint_area_m2),
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": out_features}


# ---------------------------------------------------------------------------
# measures.json: config/measures.json（正本）を web/lib/join.js・web/app.js が
# 期待する形式（{score_version, measures: [{id, title, condition}]}）に変換する。
# app.js は id / title のみ参照する（joinBuildingsWithAssessments は measures.json
# を扱わない）。condition は人間が読む補助情報として、条件ツリーを日本語風の
# 短い文字列に機械的に変換したもの。数値・条件そのものは変更しない。
# ---------------------------------------------------------------------------

_OP_JA = {
    "eq": "=",
    "ne": "≠",
    "in": "のいずれか",
    "not_in": "のいずれでもない",
    "gte": "≥",
    "lte": "≤",
    "gt": ">",
    "lt": "<",
    "is_true": "= true",
    "is_false": "= false",
    "not_null": "が既知",
    "is_null": "が不明",
    "always": "常に真",
}


def _short_path(path: str) -> str:
    """"features.rel_elev_m" -> "rel_elev_m"、"answers.q03" -> "Q3" のように短縮する。"""
    bucket, _, key = path.partition(".")
    if bucket == "answers" and key.startswith("q") and key[1:].isdigit():
        return f"Q{int(key[1:])}"
    return key or path


def _render_condition(cond: dict[str, Any]) -> str:
    if "all" in cond:
        return "(" + " かつ ".join(_render_condition(c) for c in cond["all"]) + ")"
    if "any" in cond:
        return "(" + " または ".join(_render_condition(c) for c in cond["any"]) + ")"
    if "not" in cond:
        return "NOT " + _render_condition(cond["not"])

    op = cond["op"]
    if op == "always":
        return _OP_JA["always"]
    key = _short_path(cond.get("path", ""))
    if op in ("is_true", "is_false", "not_null", "is_null"):
        return f"{key} {_OP_JA[op]}"
    value = cond.get("value")
    if op in ("in", "not_in") and isinstance(value, list):
        return f"{key} {_OP_JA[op]}（{', '.join(str(v) for v in value)}）"
    return f"{key} {_OP_JA.get(op, op)} {value}"


def build_measures_json(measures_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "score_version": measures_config.get("score_version"),
        "measures": [
            {"id": m["id"], "title": m["title"], "condition": _render_condition(m["condition"])}
            for m in measures_config["measures"]
        ],
    }


# ---------------------------------------------------------------------------
# 生成本体
# ---------------------------------------------------------------------------


def build(
    *,
    features_path: Path = DEFAULT_FEATURES_CSV,
    answers_path: Path | None = DEFAULT_ANSWERS_CSV,
    measures_config_path: Path = DEFAULT_MEASURES_CONFIG,
    scoring_config_path: Path | None = None,
    assessments_out: Path = DEFAULT_ASSESSMENTS_OUT,
    buildings_out: Path = DEFAULT_BUILDINGS_OUT,
    measures_out: Path = DEFAULT_MEASURES_OUT,
    computed_at: str = FIXED_COMPUTED_AT,
) -> dict[str, Any]:
    """features/answers から floodbcp を実行し、web/data/ の3ファイルを生成する。

    入力（features_path・answers_path・各 config）が同じであれば、常に同一の
    出力になる（computed_at を固定しているため。building_id ハッシュシードにより
    ポリゴン生成も決定的）。戻り値は生成サマリ（CLI 表示・テスト用）。
    """
    features = load_features(features_path)
    answers_map = load_answers_csv(answers_path) if answers_path else {}

    scoring_config = load_scoring_config(scoring_config_path) if scoring_config_path else load_scoring_config()
    measures_config = load_measures_config(measures_config_path)

    assessments = [
        assess(
            f,
            answers=answers_map.get(f.building_id),
            config=scoring_config,
            measures_config=measures_config,
            computed_at=computed_at,
        )
        for f in features
    ]

    # web/ ビューア（TASK-005、web/tests/join.test.js）は「status が out_of_scope で
    # なければ priority は A/B/C/D のいずれか」という前提でテストされている
    # （TASK-005 当時の手書きサンプルがそう作られていたため）。しかし
    # docs/03_スコアリング仕様.md の実装上、status=insufficient_data は H が
    # 算出できず P・priority も必ず null になる（H が None のため P 行列を
    # 引けない）。この前提が実際の評価エンジンの出力と食い違うため、
    # web/data/ 向けにはこの1件だけを除外する（floodbcp の実出力は書き換えず、
    # 除外するだけ）。data/samples/ 自体・floodbcp CLI・他のテストは
    # insufficient_data を含む全件をそのまま扱う（tests/test_cli.py 参照）。
    web_pairs = [(f, a) for f, a in zip(features, assessments) if a.status != "insufficient_data"]
    web_features = [f for f, _ in web_pairs]
    web_assessments = [a for _, a in web_pairs]

    assessments_out = Path(assessments_out)
    buildings_out = Path(buildings_out)
    measures_out = Path(measures_out)
    for p in (assessments_out, buildings_out, measures_out):
        p.parent.mkdir(parents=True, exist_ok=True)

    write_json(web_assessments, assessments_out)

    buildings_geojson = build_buildings_geojson(web_features)
    with open(buildings_out, "w", encoding="utf-8") as fh:
        json.dump(buildings_geojson, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    measures_json = build_measures_json(measures_config)
    with open(measures_out, "w", encoding="utf-8") as fh:
        json.dump(measures_json, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    counts: dict[str, int] = {}
    for a in assessments:
        key = a.priority or a.status
        counts[key] = counts.get(key, 0) + 1

    return {
        "building_count": len(features),
        "web_building_count": len(web_features),
        "priority_counts": counts,
        "assessments_out": str(assessments_out),
        "buildings_out": str(buildings_out),
        "measures_out": str(measures_out),
    }


def run_node_tests() -> int:
    node = shutil.which("node")
    if node is None:
        print("node が見つからないため node --test 'web/tests/*.test.js' はスキップします。")
        return 0
    result = subprocess.run(
        [node, "--test", "web/tests/*.test.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="data/samples/ から web/data/ のデモ用データを生成する（TASK-007）")
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES_CSV, help="features CSV/JSON Lines")
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS_CSV, help="Tier1 回答 CSV")
    parser.add_argument(
        "--skip-node-tests", action="store_true", help="生成後の node --test 実行をスキップする"
    )
    args = parser.parse_args(argv)

    summary = build(features_path=args.features, answers_path=args.answers)
    print(f"評価件数: {summary['building_count']}  優先度・ステータス内訳: {summary['priority_counts']}")
    print(
        f"web/data/ へ出力: {summary['web_building_count']} 件"
        f"（insufficient_data の {summary['building_count'] - summary['web_building_count']} 件は除外。詳細はスクリプト内コメント参照）"
    )
    print(f"生成: {summary['assessments_out']}")
    print(f"生成: {summary['buildings_out']}")
    print(f"生成: {summary['measures_out']}")

    if args.skip_node_tests:
        print("node --test はスキップしました（--skip-node-tests）。")
        return 0

    print("--- node --test 'web/tests/*.test.js' ---")
    return run_node_tests()


if __name__ == "__main__":
    raise SystemExit(main())
