"""浸水深階級コード → (min_m, max_m) 写像（純 Python、標準ライブラリのみ）。

**未検証事項（V-02 / V-05）**:
  写像テーブルの実体は `pipelines/config/depth_class_tables.json` に外出しして
  いる。同ファイルに記載の階級区分（東京都浸水予想区域図・国土数値情報
  A31/A51/A49）はいずれも docs/tasks/TASK-003_ETL骨格.md が挙げる「想定される
  階級」をそのまま設定ファイル化したものであり、**実データの属性値で検証
  していない**。ローカル環境で実ファイルを取得した後、収録されている実際の
  コード値・階級区分に本ファイル（JSON）を合わせて更新すること。
  詳細は `pipelines/README.md` の V-02 節を参照。

このモジュール自体は GIS ライブラリに依存しない（JSON 読み込みと辞書参照のみ）。
"""

from __future__ import annotations

import json
import os
from typing import Optional

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "depth_class_tables.json",
)


class DepthClassTable:
    """1 データソース分の 階級コード -> (min_m, max_m) 写像を保持する。"""

    def __init__(self, source_id: str, class_codes: dict, *, verified: bool = False, note: str = ""):
        self.source_id = source_id
        self.verified = verified
        self.note = note
        # JSON の値は [min, max_or_null] の list なので tuple に正規化する
        self._table: dict[str, tuple[float, Optional[float]]] = {}
        for code, bounds in class_codes.items():
            lo, hi = bounds[0], bounds[1]
            self._table[str(code)] = (float(lo), None if hi is None else float(hi))

    def range_for(self, class_code) -> Optional[tuple[float, Optional[float]]]:
        """階級コードから (min_m, max_m) を返す。未知コードは None。

        max_m が None の場合は「上限なし（最上位階級）」を意味する。
        """
        if class_code is None:
            return None
        return self._table.get(str(class_code))

    def codes(self):
        return list(self._table.keys())


def load_tables(config_path: str = _DEFAULT_CONFIG_PATH) -> dict[str, DepthClassTable]:
    """depth_class_tables.json を読み込み、source_id -> DepthClassTable を返す。"""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    tables: dict[str, DepthClassTable] = {}
    for source_id, spec in raw.get("sources", {}).items():
        tables[source_id] = DepthClassTable(
            source_id,
            spec.get("class_codes", {}),
            verified=bool(spec.get("verified", False)),
            note=spec.get("note", ""),
        )
    return tables


def depth_range_for_code(source_id: str, class_code, config_path: str = _DEFAULT_CONFIG_PATH):
    """source_id・class_code から (min_m, max_m) を引く便利関数。

    未知の source_id / class_code の場合は (None, None) を返す。
    """
    tables = load_tables(config_path)
    table = tables.get(source_id)
    if table is None:
        return (None, None)
    rng = table.range_for(class_code)
    if rng is None:
        return (None, None)
    return rng


def combine_max_range(
    ranges: list[Optional[tuple[Optional[float], Optional[float]]]],
) -> tuple[Optional[float], Optional[float]]:
    """建物に交差する複数階級のうち、下限が最大のものを採用する（下限で代表）。

    docs/03_スコアリング仕様.md 3-1「各ソースの階級下限を代表値とする」の
    方針に合わせ、20_hazard_join.py で「建物ごとに交差する階級の最大
    （下限・上限）を取る」処理の中核ロジックとして使う。

    None を含む要素は無視する。全て None（交差なし）の場合は (None, None)。
    """
    valid = [r for r in ranges if r is not None and r[0] is not None]
    if not valid:
        return (None, None)
    best = max(valid, key=lambda r: r[0])
    return best
