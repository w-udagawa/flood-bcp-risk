# TASK-006 M1 検証ツールキット（標準ライブラリのみ）

- 担当：Sonnet 5（実装者） 発注：Fable
- 目的：要件定義書 16 章の未検証事項 V-01〜V-12 のうち、ファイルを手元に置けば機械的に確認できるものを、GIS ライブラリなしで実行できるスクリプトにする。ユーザーはネットワーク制限のないローカル PC で実行する。
- 前提・制約：
  - 作業ディレクトリ：リポジトリルート。作成先は `tools/verify/` と `docs/07_M1検証手順書.md`、`docs/verification/`。他は触らない。
  - **Python 3.11 標準ライブラリのみ**（sqlite3、struct、csv、json、urllib、zipfile、argparse）。geopandas 等は使わない。
  - 本環境では外部サイトに到達できない。ネットワークを使う機能は「到達できなければその旨を出力して終了」する設計にし、テストではネットワークを使わない。
- 入力：`docs/02_要件定義書.md` 16 章、`docs/04_データカタログ.md` 第 5 章、`docs/research/A〜C`、`config/features_schema.json`、`pipelines/config/depth_class_tables.json`
- 出力：
  1. `tools/verify/dbf_inspect.py`：Shapefile の `.dbf` を stdlib（struct）で読み、フィールド一覧（名前・型・長さ）、レコード数、各フィールドの非 null 率、ユニーク値の上位 N（既定 20）とその件数を表示・JSON 出力する。dBase III/IV の C/N/F/L/D 型に対応。文字コードは `--encoding`（既定 cp932、失敗時 utf-8 で再試行）。zip のまま指定された場合は中の `.dbf` を探す。**用途：V-02（東京都浸水予想区域図の階級属性）、V-05（A51 の対象自治体）、A31 の属性確認**。
  2. `tools/verify/gpkg_fill_rate.py`：GeoPackage（SQLite）を sqlite3 で開き、`gpkg_contents` からレイヤ一覧を出し、指定レイヤ（既定：名前に `bldg` または `Building` を含むもの）の全列について非 null 率・非空文字率・ユニーク数を集計する。`--columns-like` で PLATEAU の関心列（`storeysBelowGround`, `storeysAboveGround`, `usage`, `yearOfConstruction`, `measuredHeight`, `totalFloorArea`, `buildingFootprintArea`, `Flooding`, `HighTide`, `Inland`, `River`, `depth`, `rank`）を優先表示。**用途：V-01（PLATEAU 属性収録率）**。列名は GIS Converter の出力に依存するため、部分一致で探す。
  3. `tools/verify/tile_probe.py`：緯度経度の bbox（既定：目黒区・世田谷区を含む概略範囲。数値はスクリプト内に定数として置き、出典を「概算」と明記）とズーム（既定 15）から地理院標高タイル URL（`dem5a`, `dem5b`, `dem1a`：`https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.txt`）を列挙し、`--fetch` 指定時のみ urllib で HEAD/GET して存在率を報告する。タイル座標計算は `pipelines/lib/tiles.py` を import して再利用する（重複実装しない）。**用途：V-03**。
  4. `tools/verify/depth_class_check.py`：`dbf_inspect.py` の JSON 出力と `pipelines/config/depth_class_tables.json` を突き合わせ、実データに現れた階級コード／ラベルのうち写像表に無いものを列挙する。**用途：V-02 の写像表更新**。
  5. `tools/verify/README.md`：各スクリプトの用途・使い方・対応する V-xx。
  6. `docs/07_M1検証手順書.md`：V-01〜V-12 を順に、「取得元 URL → 取得手順（ログイン・API キー要否）→ 実行コマンド → 記録すべき結果 → 判定基準（例：V-01 は地下階数の非 null 率 80% 以上なら Tier 0 で使用、未満なら推定ロジックを主とする）→ 結果の反映先（04 カタログ、03 仕様、pipelines/config）」の形式で書く。手作業でしか確認できない項目（V-04, V-06〜V-12）は確認画面の見方とチェック項目を書く。
  7. `docs/verification/M1_results_template.md`：結果記入用テンプレート（V-xx ごとに 実施日 / 実施者 / 結果 / 判定 / 反映先 の表）。
  8. `tools/verify/tests/test_verify.py`：unittest。テスト内で小さな `.dbf` をバイナリ生成して `dbf_inspect` を検証、`sqlite3` で `gpkg_contents` とダミー建物テーブルを作って `gpkg_fill_rate` を検証、`tile_probe` は URL 列挙のみ検証（ネットワーク不使用）、`depth_class_check` は既知コードと未知コードの検出を検証。
- 受入基準：
  - [ ] `python3 -m unittest discover -s tools/verify/tests -v` が全件成功
  - [ ] `python3 tools/verify/dbf_inspect.py --help` 等 4 スクリプトの `--help` が動く
  - [ ] `grep -rn "^import\|^from" tools/verify/*.py` に標準ライブラリと `pipelines.lib` 以外がない
  - [ ] 手順書に V-01〜V-12 が全て載り、各項目に判定基準と反映先がある
  - [ ] URL は `docs/` に既出のものだけ。捏造しない
- 禁止事項：`floodbcp/`、`pipelines/`（`lib/tiles.py` の import は可、編集は不可）、`web/`、既存 `docs/00〜06` の編集。外部サイトへのアクセス試行。git 操作。
- 完了報告に含めること：ファイル一覧、テスト結果、手順書で判定基準を決めきれなかった項目（Fable が判断する）。
