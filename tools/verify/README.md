# tools/verify/ — M1 検証ツールキット

`docs/02_要件定義書.md` 16 章の未検証事項 V-01〜V-12 のうち、ファイルを手元
に置けば機械的に確認できるものを、**GIS ライブラリなし（Python 3.11 標準
ライブラリのみ）** で検証するためのスクリプト群。ネットワーク制限のない
ローカル PC で、`docs/07_M1検証手順書.md` の手順に沿って実行することを
想定している。

依存: `sqlite3`, `struct`, `csv`, `json`, `urllib`, `zipfile`, `argparse` 等の
標準ライブラリのみ。`pipelines/lib/tiles.py`（タイル座標計算）だけは
import して再利用する（geopandas 等の GIS ライブラリは一切使わない）。

全スクリプトはネットワークを使わないのが既定動作。`tile_probe.py` の
`--fetch` を明示的に指定した場合のみ通信を試み、到達できない場合は例外で
落ちずにその旨を表示して終了する。

## スクリプト一覧

### 1. `dbf_inspect.py` — Shapefile 属性テーブル（.dbf）の検査

**対応する検証事項**: V-02（東京都浸水予想区域図の階級属性）、V-05（国土数
値情報 A51 の対象自治体。ダウンロードした Shape の属性から対象都県コードを
確認する用途）、A31 の属性確認全般。

dBase III/IV 形式の `.dbf` を `struct` でバイナリパースし、フィールド一覧
（名前・型・長さ・小数桁）、レコード数、各フィールドの非 null 率、ユニーク
値の上位 N 件（既定 20）とその件数を表示・JSON 出力する。対応フィールド型:
`C`（文字列）, `N`（数値）, `F`（浮動小数）, `L`（論理値）, `D`（日付）。
`.dbf` を直接指定するほか、Shapefile 一式を含む `.zip` をそのまま指定した
場合は中の `.dbf` を自動で探して読む（複数ある場合は `--member` で選択）。

文字コードは `--encoding`（既定 `cp932`）。指定エンコードでのデコードに
失敗した場合は `utf-8` で再試行する。

```bash
# テキストレポートを表示
python3 tools/verify/dbf_inspect.py path/to/shape.zip

# JSON も書き出す（depth_class_check.py の入力に使う）
python3 tools/verify/dbf_inspect.py path/to/shape.zip \
  --encoding cp932 --top-n 30 --json-out /tmp/dbf_result.json

--help
python3 tools/verify/dbf_inspect.py --help
```

### 2. `gpkg_fill_rate.py` — GeoPackage の属性収録率集計

**対応する検証事項**: V-01（PLATEAU 建物モデルの属性収録率）。

PLATEAU GIS Converter で CityGML から変換した GeoPackage（実体は SQLite）
を `sqlite3` で開き、`gpkg_contents` からレイヤ一覧を表示したうえで、指定
レイヤ（既定: テーブル名に `bldg` または `Building` を含むもの）の全列に
ついて非 null 率・非空文字率・ユニーク数を集計する。列名は GIS Converter の
出力バージョンに依存して揺れるため、`--columns-like` で PLATEAU の関心列
（`storeysBelowGround`, `storeysAboveGround`, `usage`, `yearOfConstruction`,
`measuredHeight`, `totalFloorArea`, `buildingFootprintArea`, `Flooding`,
`HighTide`, `Inland`, `River`, `depth`, `rank`）を部分一致で優先表示する。

```bash
python3 tools/verify/gpkg_fill_rate.py path/to/meguro.gpkg

# レイヤを明示指定し、JSON も書き出す
python3 tools/verify/gpkg_fill_rate.py path/to/meguro.gpkg \
  --layer bldg_lod1 --json-out /tmp/gpkg_result.json

--help
python3 tools/verify/gpkg_fill_rate.py --help
```

### 3. `tile_probe.py` — 地理院標高タイル URL 列挙・到達確認

**対応する検証事項**: V-03（対象区の DEM5A/DEM1A 整備状況、標高タイルの
最大ズーム）。

緯度経度の bbox（既定: 目黒区・世田谷区を含む概略範囲。**出典は「概算」**
であり、行政界データから厳密に切り出したものではない）とズーム（既定 15）
から、地理院標高タイル URL（`dem5a`, `dem5b`, `dem1a`:
`https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.txt`）を列挙する。
タイル座標の計算は `pipelines/lib/tiles.py` を import して再利用しており、
重複実装はしていない。

既定では通信を一切行わない（URL 列挙のみ）。`--fetch` を指定したときのみ
`urllib` で HEAD（405 等で拒否される場合は GET）を試行し、存在率を報告する。
本開発サンドボックスのように外部サイトに到達できない環境では、最初の
到達不能を検知した時点で残りの通信を打ち切り、「到達できませんでした」と
表示して正常終了する（例外で落ちない）。

```bash
# URL 列挙のみ（通信なし）
python3 tools/verify/tile_probe.py

# bbox・ズームを指定
python3 tools/verify/tile_probe.py --bbox 139.60,35.60,139.72,35.66 --zoom 16

# ネットワーク制限のない環境でのみ: 到達確認を行う
python3 tools/verify/tile_probe.py --fetch --max-per-layer 20 --json-out /tmp/tile_result.json

--help
python3 tools/verify/tile_probe.py --help
```

### 4. `depth_class_check.py` — 浸水深階級コードの写像表突き合わせ

**対応する検証事項**: V-02 の写像表更新（`pipelines/config/depth_class_tables.json`）。

`dbf_inspect.py --json-out` の出力（属性テーブルの各フィールドの
`top_values`）と `pipelines/config/depth_class_tables.json` の
`sources.<source>.class_codes`（コード → [下限m, 上限m]）を突き合わせ、

- 実データに現れたが写像表に無いコード／ラベル（`unmapped_in_data`）
- 写像表にはあるが実データの上位値には現れなかったコード（`unused_in_table`）

を報告する。`--field` で階級コード（またはラベル）が入っている dbf の
フィールド名を、`--source` で `depth_class_tables.json` 内のキー
（`tokyo_inundation_map` / `ksj_a31` / `ksj_a51` / `ksj_a49` /
`plateau_risk_attribute`）を指定する。

未知のコードが1件でも見つかった場合、終了コード `2` を返す（自動処理での
判定用。それ以外の異常終了は `1`、正常終了は `0`）。

```bash
# 1. まず dbf を JSON 化する（--top-n は写像表の階級数より十分大きくすること）
python3 tools/verify/dbf_inspect.py path/to/shape.zip --top-n 50 --json-out /tmp/dbf_result.json

# 2. 写像表と突き合わせる（フィールド名は 1. の出力を見て確認する）
python3 tools/verify/depth_class_check.py /tmp/dbf_result.json \
  --field 浸水ランク --source tokyo_inundation_map

--help
python3 tools/verify/depth_class_check.py --help
```

## テスト

```bash
python3 -m unittest discover -s tools/verify/tests -v
```

`.dbf` バイナリはテスト内で組み立てるため外部フィクスチャは不要。
`gpkg_fill_rate.py` のテストは一時ファイルに `sqlite3` で
`gpkg_contents` とダミー建物テーブルを作成して検証する。`tile_probe.py`
のテストは URL 列挙のみを検証し、ネットワークは使用しない。

## 制約・注意事項

- 標準ライブラリと `pipelines.lib.tiles` 以外は import しない
  （`grep -rn "^import\|^from" tools/verify/*.py` で確認可能）。
- `.dbf` のメモフィールド（`M` 型）の中身は読まない（本ツールキットの
  用途では属性の欠損率確認が主目的のため）。
- `gpkg_fill_rate.py` はジオメトリ列（`geom` 等）を読まない。存在有無や
  空間参照系（CRS）の妥当性チェックは対象外。
- `tile_probe.py` の既定 bbox はあくまで「概算」。厳密な行政界での確認が
  必要な場合は `--bbox` で上書きすること。
- URL はすべて `docs/` に既出のものだけを使用しており、捏造した URL は
  含まない。
