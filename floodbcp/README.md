# floodbcp

洪水 BCP リスク一次スクリーニング用のスコアリングエンジン（`docs/03_スコアリング仕様.md` 実装）。
Python 3.11 標準ライブラリのみで動作します（外部依存なし）。

## 設計方針

- **設定駆動**：閾値・マトリクス（H×V→P、P×I→優先度）・重み・対策候補の提示条件は
  すべて `config/scoring_v0.1.0.json` と `config/measures.json` に置き、
  `floodbcp` はそれを読み込んで評価するだけで、数値をソースコードに埋め込まない。
  条件式は `floodbcp/rules.py` の小さな汎用評価エンジン
  （`{"all"/"any"/"not": ...}` と `{"path", "op", "value"}` の木構造）で解釈する。
- **再現性**：`assess()` は入力（feature・answers・config）が同じなら常に同じ結果を返す
  （`computed_at` を明示的に渡せば完全に決定的）。
- **evidence の意味**：各等級（H/V/I/C）がどの入力・どのルールから導かれたかを
  `evidence` 配列に残す。各要素は
  `{"axis", "rule", "value", "source", "fetched_at"}` の形（仕様書第11章）。
  本スキーマ（`config/features_schema.json`）にはレコード単位の取得日フィールドが
  ないため、`source` は `data_versions`、`fetched_at` は `null` になる（詳細は
  完了報告の「仕様の曖昧点」を参照）。

## モジュール構成

- `features.py`：`Feature` データクラス、CSV/JSON Lines ローダ、型変換
  （空文字→None、"true"/"false"→bool、数値変換）、スキーマ検証（未知フィールドはエラー）。
- `questionnaire.py`：Tier1 回答（Q1〜Q12、`building_id,q01..q12`）の CSV 読込。
- `rules.py`：汎用条件式評価エンジン。
- `scoring.py`：`assess(feature, answers=None, config=None, measures_config=None, computed_at=None) -> Assessment`。
  H/V/I/C/P/priority/status/evidence/missing_info/priority_checks/measures を算出する。
- `measures.py`：`config/measures.json` の対策候補条件を評価する。
- `report.py`：`Assessment` の一覧を JSON / CSV に書き出す。
- `__main__.py`：CLI（下記）。

## CLI

```bash
cd flood-bcp-risk

# 一括評価
python3 -m floodbcp assess \
  --features data/samples/features_sample.csv \
  --answers data/samples/answers_sample.csv \
  --out /tmp/out.json \
  --csv /tmp/out.csv

# 1棟をカルテ形式で表示
python3 -m floodbcp explain \
  --features data/samples/features_sample.csv \
  --building-id bldg_sample_001 \
  --answers data/samples/answers_sample.csv
```

`--config` / `--measures-config` で設定 JSON を差し替えられる（省略時は
`config/scoring_v0.1.0.json` / `config/measures.json`）。

## テスト

```bash
python3 -m unittest discover -s tests -v
```
