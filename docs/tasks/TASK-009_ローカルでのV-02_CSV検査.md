# TASK-009 東京都浸水予想区域図 CSV の構造検査（ローカル Claude Code 向け）

- 担当：ローカル環境の Claude Code（ユーザー PC） 発注：Fable
- 目的：東京都オープンデータ「城南地区河川流域浸水予想区域図（改定） 浸水深・地盤高データ」CSV の構造を検査し、結果だけを記録して push する。判定は Fable が行う。
- 背景：調査時は Shape と推定していたが、実際は **CSV（浸水深・地盤高）+ PDF（図郭割）** で提供され、ライセンスは CC BY と明記されていた（要件定義 V-02 の前提が変わった）。
- 前提・制約：
  - 作業ディレクトリ：`C:\ClaudeWork\flood-bcp-risk`。先に `CLAUDE.md` と `docs/07_M1検証手順書.md` の V-02 節を読む。
  - Python 標準ライブラリだけで検査する（pandas 等を入れない）。
  - **生データ（CSV / zip / PDF）はコミットしない**。`data/raw/` は .gitignore 済み。
  - `docs/03`、`docs/04`、`pipelines/config`、`floodbcp/` は編集しない。
- 手順：
  1. `%USERPROFILE%\Downloads` から該当ファイル（名前に「城南」または「浸水」を含む `.csv` / `.zip`）を探し、`data\raw\tokyo_inundation_jonan\` に置く（zip は展開）。図郭割 PDF があれば同じ場所へコピーする。
  2. 検査項目：
     - 文字コード（cp932 / utf-8 / utf-8-sig）、区切り文字、ヘッダー行の有無
     - 列名一覧、行数、ファイルサイズ
     - 各列の型、非 null 率。数値列は min / max / 平均、文字列列はユニーク値上位 20 と件数
     - 座標列の特定（X/Y、緯度/経度、メッシュコード、図郭番号+行列番号 のどれか）と、値域からの座標系推定（数万〜数十万 m なら平面直角座標系第 9 系 EPSG:6677 の可能性、130〜140 / 35〜36 なら緯度経度）
     - 浸水深列：m の数値か階級コードか。階級なら全ユニーク値と件数
     - 地盤高列：単位と値域
     - 外水（河川）と内水を区別する列の有無
     - 図郭割 PDF があれば、図郭番号と CSV の対応の説明を抜き出す（読めなければ「未読」と記録）
  3. 出力：
     - `docs\verification\_work\v02_csv_summary.json`（集計を機械可読で）
     - `docs\verification\_work\v02_head.txt`（先頭 5 行。住所等があれば伏せる）
     - `docs\verification\M1_results.md`（`M1_results_template.md` をコピーし V-02 欄を記入。判定欄は「Fable 判定待ち」）
  4. `git add docs\verification` → `git commit -m "M1: V-02 東京都浸水予想区域図 CSV の構造検査結果"` → `git push origin main`
  5. 列名一覧・行数・座標系の推定・浸水深の表現（数値か階級か）を短く報告する。
- 受入基準：
  - [ ] `git ls-files data/raw` が空（生データ未コミット）
  - [ ] `origin/main` に上記 3 ファイルがある
  - [ ] 検査に外部ライブラリを使っていない
