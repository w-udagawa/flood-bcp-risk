# pipelines/ — ETL パイプライン骨格

- 対応タスク: `docs/tasks/TASK-003_ETL骨格.md`
- 上位文書: `docs/02_要件定義書.md` 第 6・9・10 章、`docs/03_スコアリング仕様.md` 第 1・2 章
- 出力: `config/features_schema.json` 準拠の `features.csv` / `features.jsonl`（floodbcp/ のスコアリングエンジンの入力）
- 対象: 目黒区（PLATEAU 2025 年度版）・世田谷区（PLATEAU 2023 年度版）

## 0. 本環境での実行状況（重要）

**本開発環境は PyPI・外部サイトに到達できないため、このディレクトリのコードは
本環境では未実行・未検証である。** 実施できたのは以下のみ:

- `python3 -m py_compile pipelines/*.py pipelines/lib/*.py`（構文検証）
- `python3 -m unittest discover -s pipelines/tests -v`（`pipelines/lib/` の純 Python 部分のみ、標準ライブラリで実行可能）

`geopandas` / `shapely` / `rasterio` / `pyproj` / `duckdb` / `requests` を使う
各スクリプト（`00_download.py` の一部、`10_`〜`60_`）は、**ネットワーク制限のない
ローカル環境**で以下の手順により実データで検証し、`docs/02_要件定義書.md` 16 章の
未検証事項 V-01〜V-06（本パイプラインが関与する範囲）を確認・更新すること。

### ローカルでの実行手順（概略）

```bash
cd flood-bcp-risk
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipelines/requirements-etl.txt
# GIS バイナリ依存が必要な場合（Ubuntu 例）:
#   sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev

# 1. 取得（手動取得分は指示表示のみ。実ダウンロードは各自ブラウザ等で実施）
python3 pipelines/00_download.py --list
python3 pipelines/00_download.py            # manual=true の全件に対し取得手順を表示
python3 pipelines/00_download.py --source-id gsi_dem5a_txt \
    --bbox 139.630,35.590,139.700,35.650 --zoom 15   # 自動取得できる標高タイルの例

# 2. PLATEAU CityGML -> GeoPackage、属性収録率レポート（V-01）
python3 pipelines/10_plateau_to_gpkg.py convert \
    --citygml data/raw/plateau/meguro_2025/udx/bldg --out data/interim/meguro_2025_bldg.gpkg
python3 pipelines/10_plateau_to_gpkg.py inspect --gpkg data/interim/meguro_2025_bldg.gpkg
python3 pipelines/10_plateau_to_gpkg.py report --gpkg data/interim/meguro_2025_bldg.gpkg \
    --out data/interim/meguro_2025_coverage_report.csv

# 3. ハザード空間結合（内水・洪水をそれぞれ実行、V-02/V-05）
python3 pipelines/20_hazard_join.py --buildings data/interim/meguro_2025_bldg.gpkg \
    --hazard-source tokyo_inundation_map --hazard-file <取得したShapeファイル> \
    --class-field <実属性名> --hazard-type inland \
    --out data/interim/meguro_2025_hazard_inland.csv

# 4. 地形特徴量（V-03）
python3 pipelines/30_terrain.py --buildings data/interim/meguro_2025_bldg.gpkg \
    --dem-dir data/raw/dem/dem5a --zoom 15 --out data/interim/meguro_2025_terrain.csv

# 5. 影響度コンテキスト
python3 pipelines/40_context.py --buildings data/interim/meguro_2025_bldg.gpkg \
    --stations <N02> --ridership <S12> --hospitals <P04> --welfare <P14> --public <P02/P05> \
    --out data/interim/meguro_2025_context.csv

# 6. 浸水実績（V-04）
python3 pipelines/50_history.py --buildings data/interim/meguro_2025_bldg.gpkg \
    --history data/manual/flood_history_meguro.geojson --out data/interim/meguro_2025_history.csv

# 7. 結合・スキーマ検証・出力
python3 pipelines/60_export_features.py \
    --buildings-gpkg data/interim/meguro_2025_bldg.gpkg --ward-code 13110 \
    --merge-csv data/interim/meguro_2025_hazard_inland.csv \
    --merge-csv data/interim/meguro_2025_terrain.csv \
    --merge-csv data/interim/meguro_2025_context.csv \
    --merge-csv data/interim/meguro_2025_history.csv \
    --out-csv data/out/features_meguro.csv --out-jsonl data/out/features_meguro.jsonl
```

世田谷区も同様に、`plateau_setagaya_2023` のデータで手順 2〜7 を繰り返す
（`--ward-code 13112`）。両区分を1つの `features.csv` にまとめる場合は
`60_export_features.py` を区ごとに実行し、出力 CSV を単純に連結すればよい
（`building_id` はグローバルに一意な PLATEAU `gml:id` のため衝突しない）。

## 1. 全体フロー

```text
manifest.json ──00_download.py──▶ data/raw/**
                                        │
data/raw/plateau/** ──10_plateau_to_gpkg.py──▶ data/interim/*_bldg.gpkg
                                        │         └─ *_coverage_report.csv (V-01)
                                        │
   ┌────────────────────────────────────┼───────────────────────────────────┐
   ▼                                    ▼                                   ▼
data/raw/hazard/**              data/raw/dem/**                    data/raw/context/**
   │20_hazard_join.py               │30_terrain.py                     │40_context.py
   ▼                                ▼                                   ▼
*_hazard_{inland,river,surge}.csv  *_terrain.csv                  *_context.csv
   │                                │                                   │
data/manual/flood_history_*.geojson (手動作成、V-04)                     │
   │50_history.py                                                       │
   ▼                                                                     │
*_history.csv                                                           │
   └──────────────┬──────────────────────────────────────────────────────┘
                   ▼
      60_export_features.py（*_bldg.gpkg の基礎属性 + 各 *.csv を building_id でマージ
                              + usage_map で usage_class 決定 + schema_check で検証）
                   ▼
      data/out/features.csv / features.jsonl  ──▶ floodbcp/（スコアリングエンジン）
```

## 2. 各ステップの入出力

| # | スクリプト | 入力 | 出力 | 備考 |
|---|---|---|---|---|
| - | `00_download.py` | `manifest.json` | `data/raw/**`（自動取得分のみ）、手動取得分は手順を標準出力に表示 | 外部サイトへの実アクセスはローカル実行時のみ発生。本開発環境では未実行 |
| 10 | `10_plateau_to_gpkg.py` | CityGML（`udx/bldg` 配下） | GeoPackage（`*_bldg.gpkg`）、属性収録率レポート CSV | PLATEAU GIS Converter（外部 CLI）を subprocess 呼び出し。V-01 対応 |
| 20 | `20_hazard_join.py` | 建物 GeoPackage + ハザード Shapefile/GeoPackage 1種 | `building_id, *_depth_min_m, *_depth_max_m` の CSV | inland/river/surge ごとに実行。V-02/V-05 対応 |
| 30 | `30_terrain.py` | 建物 GeoPackage + DEM5A txt タイル群 + 道路（任意） | `building_id, ground_elev_m, road_elev_m, rel_elev_m, depression_flag` CSV | V-03 対応。窪地判定は暫定指標（1-3節） |
| 40 | `40_context.py` | 建物 GeoPackage（usage_class 付与後推奨） + N02/S12/P04/P14/P02\|P05 | `building_id, station_ridership, is_station_facility, hospital_flag, welfare_flag, public_flag, alt_facility_dist_m` CSV | P02/P05 は URL 未確定（manifest 参照） |
| 50 | `50_history.py` | 建物 GeoPackage + 浸水実績 GeoJSON（手動作成） | `building_id, flood_history_flag, flood_history_years` CSV | V-04 対応 |
| 60 | `60_export_features.py` | 建物 GeoPackage（基礎属性） + 10〜50 の CSV 群 | `features.csv` / `features.jsonl` | usage_class 決定・`config/features_schema.json` に対する型検証を実施 |

## 3. 必要ツール

| ツール | 用途 | 入手方法 |
|---|---|---|
| Python 3.11 目安（3.10+） | 全スクリプト | ローカル環境の Python |
| `pipelines/requirements-etl.txt` の各パッケージ | GIS 処理 | `pip install -r pipelines/requirements-etl.txt` |
| PLATEAU GIS Converter | CityGML → GeoPackage 変換（`10_plateau_to_gpkg.py` が呼び出す外部 CLI） | https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter （`manifest.json` source_id=plateau_gis_converter、pip では入らない） |
| tippecanoe | features → PMTiles 生成 | pipelines/ の対象外（`tiles/` 工程で使用）。タスクカードの言及に従い記載のみ |
| GDAL バイナリ（gdal-bin 等） | geopandas/fiona/rasterio の実行時依存 | OS パッケージマネージャ（例: `apt-get install gdal-bin libgdal-dev`）または conda-forge |

## 4. 未検証事項（V-01〜V-06）への対応箇所

`docs/02_要件定義書.md` 16 章の未検証事項のうち、本パイプラインが関与するもの:

| ID | 内容 | 対応箇所 |
|---|---|---|
| V-01 | PLATEAU 建物付与の災害リスク属性・地下階数の収録率 | `10_plateau_to_gpkg.py report`（属性ごとの非null率レポート）。列名候補は同ファイル `CANDIDATE_ATTRIBUTE_COLUMNS`（未検証、実データで要更新） |
| V-02 | 東京都浸水予想区域図の属性・浸水深階級・座標系 | `pipelines/config/depth_class_tables.json`（`tokyo_inundation_map`、`verified: false`）。実ファイル取得後にコード値・区分を更新すること。`20_hazard_join.py` の `--class-field` も実属性名に合わせる |
| V-03 | 対象区の DEM5A/DEM1A 整備状況、標高タイル最大ズーム | `30_terrain.py`（DEM が無いタイルは `ground_elev_m`/`road_elev_m` が null になる設計）。整備状況の確認自体は `https://maps.gsi.go.jp/development/demtile.html` をローカルで直接確認する必要あり（本環境未確認） |
| V-04 | 東京都水害リスク情報システムの浸水実績がダウンロード可能か | `manifest.json` の `tokyo_flood_history_system`。不可の場合のフォールバック（区の実績図 PDF を手動ポリゴン化）は `50_history.py` の入力（`data/manual/flood_history_*.geojson`）として設計済み |
| V-05 | 国土数値情報 A51（内水）に東京都・神奈川県が収録されているか | `manifest.json` の `ksj_a51_inland`、`depth_class_tables.json` の `ksj_a51`（`verified: false`）。収録がない場合は A51 マージをスキップし、東京都浸水予想区域図のみで内水を評価する運用になる |
| V-06 | 地理院 地形分類ベクトルタイルの URL・属性コード | `manifest.json` の `gsi_landform_classification_tiles`。実タイル URL 未確定のため、`20_hazard_join.py` の landform_class 結合は本骨格では未実装（TODO、下記「設計上の未決事項」参照） |

V-07〜V-10（不動産情報ライブラリ API、都市計画基礎調査、重ねるハザードマップ内水タイル、
国土数値情報利用規約）は本パイプラインの直接の入出力には含めていない。将来、
`20_hazard_join.py`／`manifest.json` のクロスチェック用ソースとして追加検討する。

## 5. 依存ライブラリの扱い（受入基準対応）

- `10_plateau_to_gpkg.py` 〜 `60_export_features.py` は、`geopandas` 等の重い依存を
  モジュール冒頭で `try/except ImportError` により読み込み、未インストール時は
  `_require_geopandas()` 等のガード関数が呼び出し時に分かりやすいエラーを送出する。
  これにより `python3 -m py_compile pipelines/*.py` は依存未インストールでも成功する。
- `pipelines/lib/`（`usage_map.py` / `depth_classes.py` / `tiles.py` / `csv_io.py` /
  `schema_check.py`）は標準ライブラリのみに依存し、`pipelines/tests/test_lib.py` で
  `python3 -m unittest discover -s pipelines/tests -v` により検証済み（33 テスト、全て pass）。

## 6. 設計上の未決事項（Fable が判断するもの）

TASK-003 の実装過程で、要件定義・スコアリング仕様に明記が無く、実装者の判断で
仮決めした点。ローカル環境での検証結果を踏まえ、Fable が正式に決定・仕様書へ
反映することを想定する。

1. **PLATEAU usage コード表自体が未検証**（`docs/research/A_建物データ調査.md` も
   同旨）。`pipelines/lib/usage_map.py` の `USAGE_CODE_TABLE` はタスクカード記載の
   コードのみを対象に仮の対応を付けた。特に 403（宿泊施設）・422（文教厚生施設）・
   431（運輸倉庫施設）・441（工場）・453（防衛施設）は本システムの usage_class
   区分に一対一で対応しないため、実データ確認後に再検討が必要。
2. **hospital / datacenter / welfare / station の判定方法**: PLATEAU usage コード
   単体では判別できないため、P04/P14/N02 との空間結合結果（フラグ）で上書きする
   設計とした（`usage_map.determine_usage_class` のヒント引数）。この優先順位
   （hospital_flag > datacenter_hint > station_hint > welfare_flag > public_hint >
   usage_code）は仕様書に明記が無く、実装者判断。
3. **datacenter_hint の算出方法が未実装**: データセンターを機械的に判定する
   データソースが調査 A〜C で見つかっていない（名称パターンマッチ等が必要）。
   `40_context.py` は現時点で datacenter_hint を算出しない（常に False）。
4. **alt_facility_dist_m の「同用途」の粒度**: 仕様書は「商業・医療のみ算出」と
   するが、commercial と commercial_large を同一視するかは未規定。本実装は
   `usage_class` の完全一致を採用。
5. **landform_class（地形補正）の空間結合は未実装**: V-06（タイル URL・属性
   コード未確定）のため、`20_hazard_join.py` は inland/river/surge の深さのみを
   対象とし、`landform_class` 列は現状 features に反映されない
   （`config/features_schema.json` 上は null 許容のため出力自体は可能）。
6. **窪地判定（depression_flag）は暫定指標**: Priority-Flood 等の本格手法は未実装。
   `30_terrain.py` の `compute_depression_flag()` のみを差し替えれば良い設計だが、
   richdem/whitebox 導入の要否・閾値 0.3m の妥当性は検証集合での検証が必要。
7. **国土数値情報 P02/P05 の具体的な取得 URL が調査 A〜C に無い**: `manifest.json`
   では `url: null, manual: true` とした（URL 捏造の禁止事項に従う）。ローカルで
   nlftp.mlit.go.jp の datalist ページから該当製品（官公署 P02 / 市区町村役場等
   P05 に相当するもの）を特定する作業が必要。
8. **road_elev_m の距離計算は簡易実装**（`30_terrain.py`）: EPSG:4326 上での度単位
   バッファを使っており、DR-02 が求める平面直角座標系（EPSG:6677）への投影は
   本骨格では未実施（TODO として明記）。`20_hazard_join.py`/`40_context.py`/
   `50_history.py` は EPSG:6677 に投影して処理する一方、`30_terrain.py` は
   DEM タイル座標系（Web メルカトル相当の経度緯度）との対応上、簡易実装のままに
   した。精度が問題になる場合は投影ベースのバッファ計算に置き換えること。
9. **hazard_source_year を一括指定にしている**（`60_export_features.py` の
   `--hazard-source-year`）: 実際にはハザードソースごとに公表年が異なりうる
   （東京都浸水予想区域図と国土数値情報 A31 で別年度）。仕様書 7 章 C の
   「ハザードデータの公表年が10年超なら-10」の判定をどのソース年で行うかは
   要決定。現状は建物単位で単一の年を持つ簡易実装。
