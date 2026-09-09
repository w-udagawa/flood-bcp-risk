# TASK-008 ビューアで「評価不能」を明示表示する／サンプル名から実在地名を除く

- 担当：Sonnet 5（実装者） 発注：Fable
- 目的：
  1. `status = insufficient_data`（H が算出不能、priority = null）の建物を、ビューアで除外せず「評価不能」として表示する（要件定義 5-3・FR-04・FR-07。「情報がない＝安全」と誤認させないための必須表示）。`scripts/build_demo.py` の除外処理を撤去する。
  2. 架空サンプルの名称に「自由が丘駅」など実在の駅名・地名が含まれている。名称を実在地名を含まない架空名に置き換える（例：「架空:A駅ビル」「架空:北ブロック商業棟」）。区名（目黒・世田谷・大田）も名称からは外す。
- 前提・制約：
  - 作業ディレクトリ：リポジトリルート。編集可：`web/lib/join.js`、`web/app.js`、`web/index.html`、`web/tests/`、`web/README.md`、`scripts/build_demo.py`、`data/samples/features_sample.csv`、`data/samples/README.md`、`tests/`。`floodbcp/` と `docs/` は触らない。
  - Node は `/opt/node22/bin/node`（`node --test 'web/tests/*.test.js'`）。ブラウザ確認は不可。
- 入力：`docs/03_スコアリング仕様.md` 10〜11 章、`web/lib/join.js`、`web/app.js`、`web/tests/join.test.js`、`scripts/build_demo.py`、`data/samples/`
- 出力：
  1. `web/lib/join.js`：priority が null かつ status が `insufficient_data` の建物に対し、色分けキー `unassessed`（灰色ハッチ相当の色。既存の D の灰とは区別できる色）とラベル「評価不能（データ不足）」を返す。`out_of_scope` は従来どおり「対象外」。既存の色関数・ラベル関数の契約（関数名・引数）は変えない。
  2. `web/app.js` / `web/index.html`：凡例に「評価不能」を追加。カルテで status = insufficient_data のとき、優先度欄に「評価不能」、H・P 欄に「—」、不足情報を強調表示（データ不足である旨の一文を添える）。フィルタ「優先度」に「評価不能」を選べる項目を追加。
  3. `web/tests/join.test.js`：前提「out_of_scope 以外は priority が A〜D」を撤去し、insufficient_data → unassessed のテストを追加。
  4. `scripts/build_demo.py`：insufficient_data の除外を撤去し、全建物を `web/data/` に出す。`tests/test_build_demo.py` の期待値を更新（building_id 集合が features と一致）。
  5. `data/samples/features_sample.csv` の name 列を置換。`scripts/build_demo.py` を再実行して `web/data/` を再生成。`data/samples/README.md` に「名称は全て架空で実在地名を含まない」と明記。`tests/` に名称の実在地名チェック（`自由が丘`, `目黒`, `世田谷`, `大田`, `渋谷`, `武蔵小杉` を含まない）を 1 件追加。
  6. `web/README.md` の「サンプルデータについて」を更新（除外していない旨）。
- 受入基準：
  - [ ] `python3 -m unittest discover -s tests -v` 全件成功
  - [ ] `python3 scripts/build_demo.py` 後、`node --test 'web/tests/*.test.js'` 全件成功、`node --check web/app.js web/lib/join.js` 成功
  - [ ] `web/data/assessments_sample.json` に status = insufficient_data の要素が含まれ、priority が null のまま
  - [ ] `grep -n "自由が丘\|目黒\|世田谷\|大田\|渋谷" data/samples/features_sample.csv web/data/*.json web/data/*.geojson` がヒットしない（ward_code の数値は可）
- 禁止事項：`floodbcp/`・`docs/`・`config/` の編集。評価結果（priority/status）の改変。git 操作。
- 完了報告に含めること：ファイル一覧、テスト結果、置換した名称の対応表。
