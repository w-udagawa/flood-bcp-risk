# flood-bcp-risk — 浸水時事業停止リスク診断（PoC）

オープンデータから「浸水した場合に建物機能・事業が長期停止しやすい建物」を建物単位で一次スクリーニングし、根拠・不足情報・対策候補を提示するツールの PoC。

## 文書

| 文書 | 内容 |
|---|---|
| `docs/00_オーケストレーション計画.md` | 上位モデルが計画・監督、下位モデルが実装する運用ルール |
| `docs/01_再検討メモ.md` | 初期検討資料をゼロから再検討した判断の記録 |
| `docs/02_要件定義書.md` | **確定版要件定義**（決定事項・スコープ・機能/非機能要件・データ要件・PoC 計画・未検証事項） |
| `docs/03_スコアリング仕様.md` | 等級（H/V/I/C）とマトリクス（P、優先度）の仕様。実装の唯一の根拠 |
| `docs/04_データカタログ.md` | オープンデータ台帳（`data/catalog.json` と対応） |
| `docs/05_検証事例集.md` | PoC 検証に使う被災・非被災事例 |
| `docs/06_設計判断ログ.md` | 実装者からの曖昧点・未決事項に対する判断の記録 |
| `docs/research/` | 調査レポート（WebSearch ベース。未検証事項を明記） |
| `docs/tasks/` | 下位モデルへのタスクカード |
| `docs/source/` | 元の初期検討資料 |

## 構成

```text
floodbcp/     スコアリングエンジン（Python 標準ライブラリのみ）
config/       features スキーマ、スコアリング設定、対策メニュー
pipelines/    ETL（GIS 依存。ローカル環境で実行）
web/          静的ビューア試作（MapLibre GL JS、CDN 読込）
data/         データ台帳、サンプル（架空）
tests/        スコアリングエンジンのテスト
```

## 使い方（スコアリングエンジン）

```bash
python3 -m unittest discover -s tests -v
python3 -m floodbcp assess --features data/samples/features_sample.csv \
  --answers data/samples/answers_sample.csv --out out.json --csv out.csv
python3 -m floodbcp explain --features data/samples/features_sample.csv --building-id <id>

# FR-11: 評価結果からレポート（優先現地調査リスト・管理施設一覧、CSV/UTF-8 BOM付き）を出力する
python3 -m floodbcp report --assessments out.json \
  --features data/samples/features_sample.csv \
  --priority-list priority.csv --facility-list facilities.csv
```

## デモ用データの生成（web/ ビューア向け）

`web/data/` の `assessments_sample.json` / `buildings_sample.geojson` / `measures.json` は
手書きせず、以下のスクリプトで `data/samples/` と `floodbcp` の実出力・`config/measures.json`
から生成する（TASK-007。二重管理を避け、ビューアのデータが常にスコアリングエンジンの
実出力と一致することを保証する）。

```bash
python3 scripts/build_demo.py
```

生成後、自動で `node --test 'web/tests/*.test.js'` を実行して結果を表示する
（node が見つからない場合はスキップ表示のみ）。

## 免責

本ツールの出力はオープンデータによる一次スクリーニングであり、建物の安全性や被害の有無を保証するものではない。詳細は要件定義書 D-15 と NFR-08 を参照。
