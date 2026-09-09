# 地形・標高・河川・道路・土地利用 基盤系データ & GIS処理技術 調査（C: 基盤データ編）

対象：浸水時に建物機能・事業継続が長期停止しやすい建物の一次スクリーニングアプリ
対象地域第一候補：東急線沿線（目黒区・世田谷区・渋谷区・大田区、川崎市・横浜市の一部）
調査方法：WebSearch のみ（WebFetch不可）。日英混合で30件以上検索。

---

## 要約（結論）

1. 標高は**地理院標高タイル（DEM5A/5B/10B、PNG/txt、出典明示で商用可）**が第一候補。基盤地図情報の生データDLは要ログイン（無料登録）だがタイルはログイン不要で即利用可能、これが実装上の最短経路。
2. 東急線沿線（目黒区・世田谷区・渋谷区・大田区、川崎市南部）はDEM5A（航空レーザ5m）の整備エリアである可能性が高いが、区画単位の整備状況は地理院地図の整備状況ビューアで個別確認が必須（未確認）。
3. 地形分類は「ベクトルタイル地形分類（自然地形・人工地形）」と「治水地形分類図」の2系統があるが、**治水地形分類図は国管理河川の平野部が対象で、目黒川・呑川など中小河川・都市化された東急線沿線を十分カバーしない可能性が高い**（要検証）。谷底低地・旧河道の判定はDEMからの独自解析（窪地・凹地抽出）で補完する設計が現実的。
4. 河川データ（国土数値情報W05）は水系・法河川の位置は取れるが、**暗渠区間の情報は原則載っていない**。目黒川・呑川・九品仏川は下流・上流部の一部が暗渠/覆蓋化されており、専用オープンデータは今回の調査では確認できず（区・都の公式ページに記述はあるが機械可読データの所在は未確認）。
5. 下水道台帳（東京都下水道局SEMIS）はWeb公開されているが、**オープンデータ（一括ダウンロード可能な機械可読形式）としての提供は確認できず**、Web図面ビューア中心と推定。合流式区域の広がりは自治体資料からの手動抽出が必要になりそう。
6. 地下街・地下鉄駅出入口の位置情報は国交省の全国地下街リスト（PDF中心）、鉄道会社別オープンデータ（東京メトロ→ODPT移管、東急電鉄の単独オープンデータは未確認）に分散しており、**建物単位の「地下入口」座標を機械可読で網羅取得できるソースは今回未発見**（要追加調査、OSMが最も現実的な代替）。
7. 「建物入口が道路より低い」の直接推定に関する先行研究はヒットせず。近い事例として、高解像度DEM×機械学習による内水浸水リスク評価（道路ネットワークデータ利用）や、PLATEAU建物高さ×浸水深による建物単位リスク判定の事例が存在（土木学会論文、PLATEAU UseCase）。
8. 窪地・集水面積の算出はPython生態系（richdem, pysheds, WhiteboxTools）で実用十分。QGIS/GRASS/SAGAもLinux(Ubuntu)導入が容易で、PostGIS連携も一般的。
9. 技術スタックはMapLibre GL JS + PMTiles（tippecanoeでビルド）でサーバレス静的配信が可能（S3等に置くだけ）。3D表現が必要ならCesiumJS+PLATEAU 3D Tilesを追加。バックエンドはFastAPI+PostGIS（GeoAlchemy2）が定番。分析用途はDuckDB spatialも有力候補（サーバレス、単一マシンで高速）。
10. 建物単位の分析対象データとしてPLATEAU建物モデル（属性：高さ、用途、築年等、CC BY 4.0で商用可）が最重要候補。国土数値情報「洪水浸水想定区域（A31）」には家屋倒壊等氾濫想定区域も含まれ、本アプリの浸水リスク元データとして直接使える。

---

## データ一覧表

| データ名 | 提供元 | 対象範囲・年度 | 形式 | 取得URL | ライセンス・商用利用 | 本アプリでの用途 | 確からしさ |
|---|---|---|---|---|---|---|---|
| 標高タイル DEM5A/5B/10B（txt） | 国土地理院 | 全国（整備地域差あり、東急線沿線は未確認） | XYZタイル `.txt`（カンマ区切り標高値） | `https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt` 等（demtile.html参照） | 出典明示で無償・商用可（標高タイルは基本測量成果ではなく申請不要） | 建物周辺の微地形・凹地抽出の基礎DEM | 確認済み（URL形式・利用可否）／整備範囲は推定 |
| 標高タイル DEM5A/5B/10B（PNG） | 国土地理院 | 同上 | XYZタイル `.png`（標高符号化PNG） | `https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{x}/{y}.png`、`dem5b_png`、`dem_png`（10B相当・合成） | 同上 | Web地図でのクライアントサイド標高取得・陰影表現 | 確認済み（URL存在）／各タイルの最大ズーム値は要現地確認（demtile.html） |
| 基盤地図情報 数値標高モデル（生データDL） | 国土地理院 基盤地図情報ダウンロードサービス | DEM5A=航空レーザ, DEM5B=写真測量, DEM1A=1mメッシュ（2023年11月提供開始・2025年3月大幅拡大） | XML(JPGIS)/GML | `https://service.gsi.go.jp/kiban/` | 無償・商用可・出典明示。**利用者登録（無料）とログインが必須** | 高精度解析用の生DEM取得（タイルで不足する場合の代替） | 確認済み（要ログイン点） |
| PLATEAU 地形（Terrain）データ | Project PLATEAU 配信サービス／G空間情報センター | 全国主要都市 | 3D Tiles（quantized-mesh的地形タイル） | `https://docs.plateauview.mlit.go.jp/datasets/terrain/` | PLATEAUデータは公共データ利用規約(1.0)/CC BY 4.0等でCC BY相当、商用可 | 3D可視化時の地形土台（実体はGSI DEM5m/10mメッシュから生成） | 確認済み（出典＝GSI DEMの合成である点も確認） |
| ベクトルタイル「地形分類」（自然地形・人工地形） | 国土地理院 | 全国（土地分類基本調査ベース、2021年6月公開） | ベクトルタイル（MVT） | 地理院タイル一覧 `https://maps.gsi.go.jp/development/ichiran.html` 経由で取得（実データURLは要確認） | 出典明示で無償・商用可 | 谷底低地・旧河道・盛土地等の内水リスク属性の一次スクリーニング | 確認済み（存在・概要）／実タイルURL・属性値の詳細は未確認 |
| 治水地形分類図 | 国土地理院 | 国管理河川の平野部が中心（多摩川・荒川等の大河川。目黒川・呑川等の中小河川は対象外の可能性大） | 地理院タイル、e-Govデータポータル経由の画像/GISデータ | `https://www.gsi.go.jp/bousaichiri/fc_index.html`、`https://data.e-gov.go.jp/data/dataset/mlit_20140919_3031` | 出典明示で無償・商用可 | 旧河道・自然堤防・後背低地の判定（対象河川に限る） | 確認済み（対象範囲の限定性）／東急線沿線での実カバー有無は未確認 |
| 明治期の低湿地データ | 国土地理院 | 関東地区・主要都市周辺など複数地区（対象地域含むか要確認） | 地理院タイルPNG | `https://cyberjapandata.gsi.go.jp/xyz/swale/{z}/{x}/{y}.png` | 出典明示で無償・商用可 | 明治期の水田・湿地→液状化・内水リスクの補助指標 | 確認済み（URL・概要）／東急線沿線の整備有無は未確認 |
| 土地条件図 | 国土地理院 | 全国主要都市圏（沿岸部・低地中心、東京圏含む） | 地理院タイル/PDF | `https://www.gsi.go.jp/bousaichiri/lc_index.html` | 出典明示で無償・商用可 | 地形分類の代替・補完データ | 確認済み（概要）／対象地域の整備有無は未確認 |
| 国土数値情報 河川データ（W05） | 国土交通省（国土数値情報） | 全国、水系・河川単位 | Shapefile/GML/GeoJSON | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-W05.html` | 国土数値情報利用規約：出典明示で無償・商用可 | 河川位置・氾濫源との近接性算出 | 確認済み（暗渠区間非収録は推定） |
| 国土数値情報 洪水浸水想定区域（A31） | 国土交通省（国土数値情報） | 河川単位、複数年度（最新令和7年度） | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31.html` | 出典明示で無償・商用可 | 浸水深・浸水継続時間・家屋倒壊等氾濫想定区域の一次スクリーニング指標（本アプリの主要入力候補） | 確認済み |
| 東京都下水道局 下水道台帳（SEMIS） | 東京都下水道局 | 東京都区部（1/500図面） | Web図面ビューア（機械可読データの有無不明） | `https://www.gesuijoho.metro.tokyo.lg.jp/semiswebsystem/` | 不明（オープンデータカタログ登録は未確認） | 合流式区域・下水道管情報（内水リスク補助） | 確認済み（Web公開の事実）／オープンデータ形式提供は未確認・要検証 |
| 目黒川・呑川・九品仏川 暗渠情報 | 目黒区・東京都建設局等 | 各区管理河川 | Webページ記述のみ（機械可読データ未発見） | `https://www.city.meguro.tokyo.jp/shigoto/kasen/index.html`、`https://www.kensetsu.metro.tokyo.lg.jp/river/seibi/nomikawa` | 不明 | 暗渠部（旧河道）を建物直下リスクとして扱う際の裏付け | 確認済み（暗渠化の事実）／オープンデータ非存在の可能性が高い（推定） |
| 世田谷区 GISオープンデータ | 世田谷区 | 世田谷区内 | GIS各種（ArcGIS Hub） | `https://data-setagaya.opendata.arcgis.com/` | 区のオープンデータ利用規約（多くはCC BY相当） | 公共施設・地域属性の補完 | 確認済み（サイト存在）／暗渠等具体データの有無は未確認 |
| 東京都オープンデータカタログ（土地利用現況調査GIS） | 東京都都市整備局 | 23区・多摩地域、複数年度（1986〜2022） | Shapefile | `https://catalog.data.metro.tokyo.lg.jp/dataset/t000008d2000000019` | 東京都オープンデータ利用規約（CC BY相当、商用可） | 土地利用現況（建物用途・密度）の把握 | 確認済み |
| 国土数値情報 土地利用細分メッシュ（L03-b） | 国土交通省 | 全国、100mメッシュ | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b.html` | 出典明示で無償・商用可 | 土地利用の広域スクリーニング（建設用途分布等） | 確認済み |
| 国土数値情報 用途地域（A29） | 国土交通省 | 全国、市区町村単位 | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A29-v2_1.html` | 出典明示で無償・商用可 | 用途地域による建物属性補完 | 確認済み |
| 国土数値情報 道路データ（N01） | 国土交通省 | 全国 | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gmlold/datalist/gmlold_KsjTmplt-N01.html` | 出典明示で無償・商用可 | 道路と建物の相対標高比較（入口高低差の推定材料） | 確認済み（データ自体は道路種別中心で高精度中心線ではない点に留意、推定） |
| 国土数値情報 鉄道データ（N02） | 国土交通省 | 全国 | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v2_3.html` | 出典明示で無償・商用可 | 東急線路線・駅位置の基礎データ | 確認済み |
| 国土数値情報 駅別乗降客数（S12） | 国土交通省 | 全国、複数年度（最新は2024年度版が確認できる範囲） | Shapefile/GML | `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v2_3.html` | 出典明示で無償・商用可 | 駅周辺の重要度（事業継続影響度）の重み付け | 確認済み |
| 国土数値情報 位置参照情報（街区レベル） | 国土交通省 | 全国 | Shapefile/CSV | `https://nlftp.mlit.go.jp/isj/` | 出典明示で無償・商用可 | 住所→座標のジオコーディング | 確認済み |
| 全国地下街一覧 | 国土交通省 | 全国主要地下街 | PDF（機械可読データではない） | `https://www.mlit.go.jp/common/001005390.pdf` | 政府資料、引用は可能（二次利用条件は個別確認要） | 地下街建物の抽出（PDFから手動/OCR変換が必要） | 確認済み（PDF形式の事実）／機械可読オープンデータは未発見 |
| 東京公共交通オープンデータ（ODPT） | 公共交通オープンデータ協議会（旧東京メトロ開発者サイトは2022年3月終了） | 17社局の鉄道（東京メトロ含む） | API（駅時刻表・運行情報等） | `https://developer.odpt.org/ja/info`、`https://tokyochallenge.odpt.org/` | 要API登録、利用規約に従う（多くは無償・要帰属表示） | 駅施設・出入口情報（東急含むか要確認） | 確認済み（プラットフォーム存在）／東急電鉄・駅出入口座標の収録有無は未確認 |
| PLATEAU 3D都市モデル（建物モデル） | Project PLATEAU／G空間情報センター | 東京都23区含む主要都市（2020年度データ等） | CityGML, 3D Tiles, GeoPackage, MVT | `https://www.geospatial.jp/ckan/dataset/plateau`、`https://docs.plateauview.mlit.go.jp/` | 公共データ利用規約(1.0)/CC BY 4.0/ODbL等、無償・商用可 | 建物単位の高さ・用途・築年属性、浸水深との重ね合わせによるリスク判定 | 確認済み（ライセンス・商用可） |

---

## 窪地・流入集中性の算出手法と推奨ツール

### 手法の要点（確認済み・一般的知見）
- **Depression filling（窪地充填）**：DEM中の局所的な凹地（sink）を、水があふれて流れ出るまで標高を持ち上げて解消する前処理。代表アルゴリズムはPriority-Flood（Barnes et al.）。
- **Flow direction（流下方向）**：D8（8方向最急降下）、D∞、MFD（マルチフロー）などのアルゴリズムでセルごとの水の流出方向を決定。
- **Flow accumulation（集水面積）**：流下方向を集積し、各セルに流れ込む上流セル数（＝集水面積）を計算。値が大きいセル＝雨水が集中しやすい＝内水リスクが高い場所の指標になる。
- **窪地そのものの検出（Depression detection）**：Fill前後のDEM差分（Fill-Original）が0より大きいセル＝窪地内部、として抽出できる（RichDEM/WhiteboxToolsで標準的手法）。

### ツール比較
| ツール | 言語/環境 | 特徴 | Ubuntu/PostGIS適合性 |
|---|---|---|---|
| **RichDEM** | Python/C++ | 並列処理、大規模DEMに強い。Depression-Filling, Flow Accumulation(D8/D∞)をAPIで提供 | pip install可、Ubuntuで導入容易（確認済み） |
| **pysheds** | Python純正 | 軽量、sinkの自動充填、D8基本、チュートリアル豊富 | pip install可、最も学習コスト低い（確認済み） |
| **WhiteboxTools** | Rust製CLI＋Python/QGISバインディング | `BreachDepressionsLeastCost`や`FillDepressions`など豊富なhydro tools、高速 | バイナリ配布でUbuntu導入容易、QGISプラグインもあり（確認済み） |
| **GRASS GIS (r.fill.dir, r.watershed)** | Cライブラリ＋GUI/CLI | r.watershedは前処理としてのdepression fillが不要（least-cost pathでスキップ可）という強み | Ubuntuリポジトリで`apt install grass`可能（確認済み、manpage存在） |
| **SAGA GIS** | C++/GUI | 豊富な水文モジュール、QGIS経由で呼び出し可 | Ubuntu対応（一般的知見、今回未詳細検証） |
| **rasterio + scipy.ndimage** | Python | DEM読み込み(rasterio)＋`ndimage.label`等でラスタのパッチ抽出・後処理に利用可能。窪地検出専用アルゴリズムは自前実装が必要 | 最も軽量、他ツールの前後処理に有用（確認済み） |

### 推奨構成（本アプリ向け）
- 前処理・解析パイプライン：**Python（rasterio でGSI標高タイルを読み込み → WhiteboxTools または RichDEM でdepression fill・flow accumulation・sink検出）**。WhiteboxToolsはCLI/Pythonバインディング双方あり、大規模処理でも高速なため第一候補。
- 建物単位の指標化：抽出した「窪地セル」「集水面積が閾値超のセル」を建物フットポリゴン（PLATEAU建物モデル or 国土地理院建物ポリゴン等）にラスタ→ベクトル集計（zonal statistics、rasterstats/rasterio+geopandas）で結合し、PostGISまたはDuckDB spatialに格納。
- 「建物入口が道路より低い」の直接推定：DEM5A（5mメッシュ）は建物1棟の入口高低差を捉えるには解像度がやや粗い可能性があるため、道路中心線（N01またはOSM）上のDEM標高と建物フットプリント境界上のDEM標高の差分を近似指標として算出する設計を推奨（先行研究は未確認、独自ロジックとして設計する必要あり）。DEM1A（1mメッシュ、整備範囲拡大中）が対象地域でカバーされていれば精度向上が期待できるため、対象4区+川崎市南部+横浜市北部のDEM1A整備状況の個別確認を優先タスクとすべき。

---

## 技術スタック推奨

| レイヤ | 候補 | コメント |
|---|---|---|
| 空間データ処理・分析 | **DuckDB spatial** または **GeoPandas** | 小〜中規模（区市町村単位の建物ポリゴン程度）であればDuckDB spatialが単一マシンで高速・サーバ不要。複雑な空間結合や運用DBとしての永続化が必要ならPostGIS。両者は排他ではなく「分析＝DuckDB、運用API＝PostGIS」の併用も可（一般的知見） |
| 永続化・API | **PostGIS + FastAPI + GeoAlchemy2** | 定番構成。ST_DWithinなどによる近接検索、建物単位の属性クエリに適する（確認済み、実装例多数） |
| 地図配信（2D） | **MapLibre GL JS + PMTiles（tippecanoeでビルド）** | S3等の静的ホスティングだけでタイル配信可能＝サーバレス実現（確認済み、日本語記事複数で実例あり） |
| 地図配信（3D） | **CesiumJS + PLATEAU 3D Tiles配信サービス** | PLATEAU公式配信サービスのURLを直接指定するだけで3D建物・地形表示が可能、ダウンロード不要（確認済み） |
| バックエンド言語 | **FastAPI（Python）** | GIS処理（rasterio/geopandas/richdem等）と同一言語で完結できる利点 |

**PMTilesでサーバレス配信は可能か**：可能（確認済み）。tippecanoeでGeoJSON/FlatGeobufからPMTilesを生成し、静的ファイルとしてS3や任意のWebサーバ・CDNに置くだけでMapLibre GL JSから直接読み込める。タイルサーバー（tileserver-gl等）の常時稼働が不要になるため、本アプリのような一次スクリーニング用途（頻繁な書き込み更新が少ない）に適している。

---

## 未確認事項・要検証リスト

1. **東急線沿線各区（目黒区・世田谷区・渋谷区・大田区）および川崎市・横浜市該当エリアのDEM5A/DEM1A整備状況** — 地理院地図の整備状況ビューアで個別メッシュ確認が必要。
2. **標高タイル各解像度（dem5a_png, dem5b_png, dem_png）の正確な最大ズームレベル** — `https://maps.gsi.go.jp/development/demtile.html` の一次情報を直接確認する必要あり（WebFetch不可のため今回未取得）。
3. **地形分類ベクトルタイルの実タイルURLパターンと属性スキーマ（谷底低地・旧河道等のコード値）** — `https://maps.gsi.go.jp/development/ichiran.html` の一覧から個別URL・凡例PDFの確認が必要。
4. **治水地形分類図の対象範囲が目黒川・呑川流域を含むか** — 国管理河川（多摩川本川等）中心のため、支流・中小河川である目黒川・呑川・九品仏川はカバー対象外の可能性が高い。含まれない場合、地形分類はDEM由来の自前解析に依存する設計が必要。
5. **東京都下水道局SEMISのデータが機械可読形式（GIS/CSV等）でオープンデータ提供されているか、Web図面ビューアのみか** — 東京都オープンデータカタログでの検索・登録有無を別途確認要。
6. **目黒川・呑川・九品仏川など暗渠区間の位置を示す機械可読オープンデータの有無** — 今回の調査では発見できず。区史・郷土資料や有志の暗渠マップ（非公式）しか存在しない可能性がある。OSMのwaterway=canal/culvertタグの充実度を別途確認する価値あり。
7. **東急電鉄が単独でオープンデータ（駅施設・出入口等）を公開しているか** — 検索で確証を得られず。ODPT経由でのデータ収録状況（事業者一覧）を個別確認する必要あり。
8. **地下街・地下駐車場・地下鉄駅出入口の座標を機械可読で網羅取得できるソース** — 国交省の全国地下街リストはPDF中心で構造化データではない。国土数値情報に「駅出入口」単体データセットは見当たらず（N02鉄道データは駅代表点のみと推定）。OSMのentrance/subway_entranceタグが代替候補になりうるが本調査では未検証。
9. **「建物入口が道路より低い」推定の先行研究・実装事例** — 学術論文・実務事例とも直接該当するものは発見できず。独自手法として設計する前提とすべき。
10. **国土数値情報 各データセットの最新年度と東急線沿線市区町村の整備有無（欠測の可能性）** — 特にA29用途地域やL03-bは自治体により整備年度が異なるため、対象4区+川崎市+横浜市それぞれの最新版年度を個別に確認する必要あり。

---

## 参照URL一覧

### 標高・地形
- https://www.gsi.go.jp/gazochosa/gazochosa41019.html （高精度標高データ）
- https://www.gsi.go.jp/kiban/ （基盤地図情報サイト）
- https://www.gsi.go.jp/kiban/faq.html （基盤地図情報FAQ、要登録の記載）
- https://service.gsi.go.jp/kiban/ （基盤地図情報ダウンロードサービス）
- https://maps.gsi.go.jp/development/demtile.html （標高タイル詳細仕様）
- https://maps.gsi.go.jp/development/hyokochi.html （標高タイルの作成方法）
- https://maps.gsi.go.jp/development/siyou.html （地理院タイルについて）
- https://maps.gsi.go.jp/development/ichiran.html （地理院タイル一覧）
- https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html （国土地理院コンテンツ利用規約）
- https://maps.gsi.go.jp/help/termsofuse.html （地理院地図 利用規約）
- https://keinkzw.com/20260612/dem1a/ （DEM1A解説記事）
- https://www.yamareco.com/modules/diary/151884-detail-359348.html （DEM1A提供範囲拡大の記録）

### 地形分類・低湿地
- https://www.gsi.go.jp/bousaichiri/lfc_index.html （ベクトルタイル「地形分類」）
- https://disaportal.gsi.go.jp/hazardmap/maps/image/chikei/index.html （土地分類基本調査 地形分類図ベクトルタイル）
- https://www.gsi.go.jp/REPORT/JIHO/vol129-abst-11.html （地形分類データ統合の論文要旨）
- https://github.com/gsi-cyberjapan/experimental_landformclassification
- https://www.gsi.go.jp/bousaichiri/fc_index.html （治水地形分類図について）
- https://www.gsi.go.jp/common/000106990.pdf （治水地形分類図解説書）
- https://www.gsi.go.jp/bousaichiri/lcmfclist.html （治水地形分類図 図名一覧）
- https://data.e-gov.go.jp/data/dataset/mlit_20140919_3031 （治水地形分類図 e-Gov）
- https://www.gsi.go.jp/bousaichiri/lc_index.html （土地条件図）
- https://www.gsi.go.jp/bousaichiri/lc_meiji.html （明治期の低湿地データ）
- https://www.gsi.go.jp/bousaichiri/bousaichiri61026.html （明治期低湿地データ 整備範囲拡大）
- https://cyberjapandata.gsi.go.jp/legend/lw_legend.pdf （明治期低湿地 凡例）

### PLATEAU
- https://docs.plateauview.mlit.go.jp/datasets/terrain/ （PLATEAU-Terrain）
- https://www.geospatial.jp/ckan/dataset/plateau （3D都市モデル ポータル G空間情報センター）
- https://www.mlit.go.jp/plateau/faq/ （PLATEAU FAQ、ライセンス）
- https://www.mlit.go.jp/plateau/use-case/uc22-009/ （高度な浸水シミュレーション ユースケース）
- https://github.com/Project-PLATEAU/plateau-streaming-tutorial

### 河川・下水道
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-W05.html （国土数値情報 河川データ）
- https://geoshape.ex.nii.ac.jp/river/ （国土数値情報河川データセット Geoshapeリポジトリ）
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31.html （洪水浸水想定区域）
- https://www.gesuijoho.metro.tokyo.lg.jp/semiswebsystem/ （東京都下水道局 下水道台帳SEMIS）
- https://www.gesui.metro.tokyo.lg.jp/contractor/daicyo （下水道台帳案内）
- https://www.city.meguro.tokyo.jp/shigoto/kasen/index.html （目黒区 河川・橋梁）
- https://www.kensetsu.metro.tokyo.lg.jp/river/seibi/nomikawa （呑川流域 東京都建設局）
- https://www.kensetsu.metro.tokyo.lg.jp/river/seibi/meguro （目黒川流域）

### 道路・鉄道
- https://nlftp.mlit.go.jp/ksj/gmlold/datalist/gmlold_KsjTmplt-N01.html （道路データN01）
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v2_3.html （鉄道データN02）
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v2_3.html （駅別乗降客数S12）
- https://nlftp.mlit.go.jp/isj/ （位置参照情報）

### 土地利用
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b.html （土地利用細分メッシュ）
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A29-v2_1.html （用途地域）
- https://catalog.data.metro.tokyo.lg.jp/dataset/t000008d2000000019 （東京都 土地利用現況調査GISデータ）
- https://www.toshiseibi.metro.tokyo.lg.jp/about/chousa/tochi_c （土地利用現況調査 概要）

### 地下空間
- https://www.mlit.go.jp/common/001005390.pdf （全国地下街一覧）
- https://www.mlit.go.jp/kokudoseisaku/kokudoseisaku_tk1_000108.html （屋内電子地図等オープンデータ化の取組）
- https://tokyochallenge.odpt.org/ （東京公共交通オープンデータチャレンジ）
- https://www.tokyometro.jp/info/212456.html （東京メトロ オープンデータ提供終了案内→ODPT移管）
- https://developer.odpt.org/ja/info （公共交通オープンデータセンター）

### 窪地・水文解析ツール
- https://richdem.readthedocs.io/en/latest/intro.html （RichDEM）
- https://richdem.readthedocs.io/en/latest/depression_filling.html
- https://richdem.readthedocs.io/en/latest/flow_accumulation.html
- https://hatarilabs.com/ih-en/elevation-model-conditioning-and-stream-network-delimitation-with-python-and-pysheds-tutorial （pysheds tutorial）
- https://jblindsay.github.io/wbt_book/available_tools/hydrological_analysis.html （WhiteboxTools 水文解析）
- https://grass.osgeo.org/grass-stable/manuals/r.fill.dir.html （GRASS r.fill.dir）
- https://ncsu-geoforall-lab.github.io/geospatial-modeling-course/grass/hydrology.html （GRASS水文チュートリアル）

### 浸水リスク関連研究
- https://www.mlit.go.jp/river/shishin_guideline/pdf/naisui_manual.pdf （内水浸水想定区域図作成マニュアル）
- https://www.jstage.jst.go.jp/article/jscejsp/71/1/71_25/_article/-char/ja/ （道路ネットワーク×機械学習の内水浸水リスク評価）

### 技術スタック
- https://duckdb.org/2023/04/28/spatial （DuckDB Spatial Extension）
- https://forrest.nyc/geospatial-tools-compared-when-to-use-geopandas-postgis-duckdb-apache-sedona-and-wherobots/ （GIS各種ツール比較）
- https://zenn.dev/fusic/articles/d4f8e6a49ae44b （PMTiles+S3 サーバレス配信）
- https://qiita.com/Kanahiro/items/577f7828c5a1e323721a （PMTilesサーバーレス配信）
- https://medium.com/@nunocarvalhodossantos/fastapi-postgis-and-geoalchemy-2-powerful-and-location-aware-web-applications-3b23f44c8fa5 （FastAPI+PostGIS+GeoAlchemy2）
- https://www.mlit.go.jp/plateau/learning/tpc06-1/ （CesiumでPLATEAU表示）
