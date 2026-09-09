# TASK-007 評価エンジン→ビューアのデモ配線とレポート出力（FR-11）

- 担当：Sonnet 5（実装者） 発注：Fable
- 目的：現在 `web/data/` の評価サンプルは手書きで、`floodbcp` の出力と一致する保証がない。評価エンジンの実出力からビューア用データを生成するスクリプトを作り、常に整合させる。あわせて FR-11 のレポート出力（優先現地調査リスト、管理施設一覧）を CLI に追加する。
- 前提・制約：
  - 作業ディレクトリ：リポジトリルート。編集可：`floodbcp/`、`tests/`、`scripts/`（新規）、`web/data/`、`web/README.md`、`README.md` の使い方節、`data/samples/`。`web/app.js`・`web/lib/join.js`・`web/index.html` は**データ契約が変わらない限り触らない**。
  - Python 標準ライブラリのみ。Node は `/opt/node22/bin/node`（`node --test`）。
  - サンプルは架空。実在の施設名・住所を使わない。
- 入力：`docs/03_スコアリング仕様.md` 11〜13 章、`docs/02_要件定義書.md` FR-11、`floodbcp/README.md`、`web/README.md`、`web/lib/join.js`（データ契約の確認）、`data/samples/`
- 出力：
  1. `floodbcp/report.py` に追加：
     - `write_priority_list_csv(assessments, path)`：優先度 A/A*/B/B* の建物を優先度順→P 降順→C 昇順で並べ、列：building_id, name, usage_class, priority, P, H, V, I, C, status, main_factors（evidence から H/V/I の主要因を日本語で 3 件まで「;」区切り）, priority_checks（「;」区切り）, measures（「;」区切り）
     - `write_facility_list_csv(assessments, path)`：全建物、列：building_id, name, ward_code, usage_class, priority, P, H, V, I, C, status, tier, computed_at
     - CSV は UTF-8 BOM 付き（Excel で開く前提）。
  2. `floodbcp/__main__.py` に `report` サブコマンド：`python3 -m floodbcp report --assessments out.json --features features.csv --priority-list priority.csv --facility-list facilities.csv`（features は name/ward_code 補完用に任意）
  3. `scripts/build_demo.py`：
     - `data/samples/features_sample.csv` と `answers_sample.csv` で `floodbcp` を実行し、`web/data/assessments_sample.json` を仕様 11 章の形式で上書き生成する（既存の手書きファイルは置き換える）。
     - `web/data/buildings_sample.geojson` を、サンプル建物 ID ごとに決定的（ID からのハッシュで乱数シード）に生成した矩形ポリゴンで上書き生成する。中心は自由が丘駅周辺（35.6075N, 139.6690E）の半径 600 m 程度。プロパティは `building_id`, `name`, `usage_class`, `ward_code`, `storeys_below`, `total_floor_area_m2`。`web/lib/join.js` が期待するプロパティ名は変えない（join.js を読んで確認）。
     - `web/data/measures.json` は `config/measures.json` から生成する（二重管理をやめる。`web/lib/join.js` が期待する形式に変換）。
     - 生成後、`node --test 'web/tests/*.test.js'` を実行して結果を表示する（Node が無ければスキップ表示）。
  4. `tests/test_report.py`：優先度順・列構成・BOM・main_factors 生成のテスト。`tests/test_build_demo.py`：一時ディレクトリで生成し、GeoJSON と assessments の building_id 集合が一致すること、決定的（2 回生成で同一）であることを検証。
  5. `README.md` の使い方節に `report` と `scripts/build_demo.py` を追記。`web/README.md` のサンプルデータの記述を「`scripts/build_demo.py` で生成」に更新。
- 受入基準：
  - [ ] `python3 -m unittest discover -s tests -v` 全件成功（既存 58 件を壊さない）
  - [ ] `python3 scripts/build_demo.py` 成功後、`node --test 'web/tests/*.test.js'` が成功
  - [ ] `web/data/assessments_sample.json` の各要素が仕様 11 章のキーを全て持つ
  - [ ] `python3 -m floodbcp report ...` で 2 つの CSV が出て、優先リストが A→B 順
  - [ ] 実在施設名なし
- 禁止事項：`docs/` の編集（README 系は除く）、`config/scoring_v0.1.0.json` の数値変更、外部依存追加、git 操作。
- 完了報告に含めること：ファイル一覧、テスト結果、サンプル 20 件の優先度分布、`web/lib/join.js` との契約で気づいた問題。
