# 建物データ調査（浸水×事業継続 一次スクリーニングアプリ向け）

調査日: 2026-09-09
調査方法: WebSearch のみ（WebFetch不可の環境制約のため、各ページの本文は未確認。検索結果スニペットとタイトルからの要約）
対象地域第一候補: 目黒区・世田谷区・渋谷区・大田区（東京都）、川崎市・横浜市の一部（神奈川県）

---

## 要約（結論）

1. 建物フットプリント＋基本属性の一次ソースは **PLATEAU（3D都市モデル）** 一択。CityGML形式で目黒区・世田谷区・渋谷区・大田区は個別区データ（2023〜2025年度）、川崎市・横浜市は市単位データ（確認できたのは2020・2022年度）が存在する（確認済み・要最新版再確認）。
2. PLATEAUのライセンスは政府標準利用規約2.0（PDL 1.0）/ CC BY 4.0 互換で、**商用利用・改変・再配布が可能**（確認済み）。これはアプリ要件上、大きな利点。
3. 浸水深・浸水継続時間などの災害リスク属性（uro:BuildingRiverFloodingRiskAttribute 等）は仕様上は建物に付与できる設計だが、**実際にどの区・どの建物にどの程度収録されているか（収録率）は今回のWebSearchでは実データを確認できなかった**。整備は自治体・年度単位で異なり、全建物一律ではなく「浸水想定区域内の建物のみ」に付与される可能性が高いと推定される（未確認・要検証）。
4. 地上/地下階数（storeysAboveGround/BelowGround）は東京23区サンプルでほぼ欠損なしとする二次情報（Zenn記事）があるが、**一次資料での検証はできていない**（推定寄り）。用途（bldg:usage）や住所は約13%程度欠損があるという同記事の言及もあり、100%収録ではない。
5. 建築面積・延床面積・構造種別（uro:BuildingDetailAttribute）は都市計画基礎調査由来のデータであり、**建物単位での整備率・収録範囲が地域ごとに大きく異なる**可能性が高い（未確認）。
6. ツールは **PLATEAU GIS Converter（Rust製、CLI/GUI、3D Tiles/MVT/GeoPackage等に変換）** と **plateau-qgis-plugin（QGIS公式プラグイン）** が最も実用的。Pythonでは **PlateauKit（旧plateaupy系）** が属性アクセス・変換の実績あり。GDALのCityGML対応は限定的（GMLASドライバで部分対応、PLATEAU専用の変換はGIS Converter推奨）。
7. PLATEAU代替/補完として **国土地理院 基盤地図情報（建築物外周線）** は全国カバレッジだが属性が乏しい（形状中心）。**Overture Maps** はOSM由来（ODbL）でPLATEAUの一部データもソースに含む。**Microsoft/Google Open Buildings は日本を主要カバレッジに含まない**（未検証だが複数傍証あり）。
8. 施設用途データは国土数値情報（P04医療機関、P14福祉施設、P29学校、S12駅別乗降客数）が定番だが、**利用規約は年度・版ごとに確認が必要**（「使用許諾条件を確認すること」という定型文言が繰り返し出るのみで、商用利用可否を明言する一次資料は未取得）。
9. 大規模小売店舗立地法の届出データは**経産省による全国一元公開が令和5年度末で終了**しており、都道府県・市単位のオープンデータに分散（確認済み）。
10. PLATEAUの浸水×建物単位リスク評価の先行事例としては **uc22-009（岡崎市・高度な浸水シミュレーション）** が建物単位の全壊・半壊リスク評価に近い内容を含む（確認済み、ただし本アプリの「事業継続」の観点は明示されていない）。

---

## データ一覧表

| データ名 | 提供元 | 対象範囲・年度 | 形式 | 取得URL | ライセンス・商用利用 | 本アプリでの用途 | 確からしさ |
|---|---|---|---|---|---|---|---|
| PLATEAU 3D都市モデル 東京都23区（一括） | 国交省/G空間情報センター | 東京23区、2020年度版・2022年度版が公開 | CityGML, 3D Tiles, MVT, FBX, OBJ 等 | https://www.geospatial.jp/ckan/dataset/plateau-tokyo23ku | 政府標準利用規約2.0/PDL1.0（CC BY 4.0互換）、商用利用可 | 建物フットプリント・基本属性のベース | 確認済み（データセット存在・年度） |
| PLATEAU 目黒区 | 同上 | 2025年度版（標準仕様書V5、CityGML/3D Tiles/MVT） | CityGML, 3D Tiles, MVT | https://www.geospatial.jp/ckan/dataset/plateau-13110-meguro-ku-2025 | 同上 | 建物属性の最新版取得 | 確認済み |
| PLATEAU 世田谷区 | 同上 | 2023年度版（標準仕様書V4） | CityGML 等 | https://www.geospatial.jp/ckan/dataset/plateau-13112-setagaya-ku-2023 | 同上 | 同上 | 確認済み |
| PLATEAU 渋谷区 | 同上 | 2025年度版 | CityGML, 3D Tiles, MVT | https://www.geospatial.jp/ckan/dataset/plateau-13113-shibuya-ku-2025 | 同上 | 同上 | 確認済み |
| PLATEAU 大田区 | 同上 | 2023年度版（標準仕様書V4） | CityGML 等 | https://www.geospatial.jp/ckan/dataset/plateau-13111-ota-ku-2023 | 同上 | 同上 | 確認済み |
| PLATEAU 川崎市 | 同上 | 2020年度版、2022年度版あり | CityGML, ジオデータベース（防災） | https://www.geospatial.jp/ckan/dataset/plateau-14130-kawasaki-shi-2022 | 同上 | 建物属性・災害リスク属性の可能性（防災用GDB） | 確認済み（存在）／内容未確認 |
| PLATEAU 横浜市 | 同上 | 2020年度版（最新版は要再確認、2020年度以降更新の可能性あり） | CityGML | https://www.geospatial.jp/ckan/dataset/plateau-14100-yokohama-city-2020 | 同上 | 建物属性ベース | 確認済み（2020年度版の存在）／最新版は未確認 |
| PLATEAU オープンデータポータル | 国交省 | 全国（2021年度56都市→2025年度末までに約300都市目標） | 各種 | https://www.mlit.go.jp/plateau/open-data/ | 同上 | データ探索の起点 | 確認済み |
| PLATEAU GIS Converter | Project-PLATEAU / MIERUNE | 全国CityGML→他形式変換ツール | Rust製 GUI/CLI | https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter | OSS（ライセンスは要individual確認、MITまたは同等の可能性・未確認） | CityGML→GeoPackage/3DTiles/MVT変換 | 確認済み（存在・機能） |
| plateau-qgis-plugin | Project-PLATEAU / MIERUNE | QGIS 3.28+、標準仕様書v3.0対応 | QGISプラグイン | https://plugins.qgis.org/plugins/plateau_plugin/ | OSS | 属性込みでQGISに読み込み・可視化・分析 | 確認済み |
| PlateauKit（旧plateaupy系譜） | ozekik | Python向けPLATEAU変換・分析ライブラリ、PlateauLab（Jupyter） | Python pkg | https://pypi.org/project/plateaukit / https://ozekik.github.io/plateaukit/ | ライセンスページあり（詳細未確認） | 建物DB構築の自動化・バッチ処理 | 確認済み（存在）／属性網羅性は未確認 |
| plateaupy（AcculusSasao） | 個人開発 | PLATEAU CityGMLパーサ・ビューア（Open3D/Blender対応） | Python | https://github.com/AcculusSasao/plateaupy | OSS（ライセンス要確認） | 3D表示・パース | 確認済み（存在） |
| PlateauUtils | Project-PLATEAU | CityGML/3DTiles/MVTをPythonに読み込む公式寄りライブラリ | Python | https://github.com/Project-PLATEAU/PlateauUtils | 要確認 | パース | 確認済み（存在） |
| GDAL GML/GMLASドライバ | OSGeo | 汎用CityGML部分対応 | ogr2ogr | https://gdal.org/en/latest/drivers/vector/gml.html | OSS(MIT/X) | 汎用変換だがPLATEAU拡張属性の完全対応は未確認 | 確認済み（機能概要）／PLATEAU適合性は未確認 |
| Flateau（Pacific Spatial Solutions） | 民間（PLATEAU由来の二次加工データ） | 全国211都市分（PLATEAU対応都市）、2D化＋メタデータ | GeoPackage, GeoParquet | https://source.coop/pacificspatial/flateau | CC-BY 4.0（PLATEAU利用規約準拠が前提） | PLATEAU建物データを軽量な2D形式で扱う代替経路 | 確認済み（存在・ライセンス） |
| 東京都都市計画基礎調査（建物現況調査） | 東京都都市整備局 | 東京都全域、標準製品仕様書あり（令和5年6月改定） | CityGML（図形）+ CSV（調書・集計表） | https://catalog.data.metro.tokyo.lg.jp/ | 要確認（東京都オープンデータ利用規約に準ずる可能性） | 階数・地下階数・構造・建築年・用途の一次情報源候補 | 推定寄り（標準仕様書の存在は確認済み、建物単位オープンデータ公開の有無・範囲は未確認） |
| 基盤地図情報（建築物外周線） | 国土地理院 | 全国 | JPGIS(GML) | https://www.gsi.go.jp/kiban/ | 無償・商用利用可（国土地理院コンテンツ利用規約、要個別確認） | 建物フットプリントの補完・検証用 | 確認済み（項目の存在）／属性内容は未確認 |
| Overture Maps Buildings | Overture Maps Foundation | 全世界（日本含む、PLATEAU由来ソースも一部含む） | GeoParquet | https://docs.overturemaps.org/guides/buildings/ | ODbL（OSM由来部分）、出典によりCC BY 4.0混在 | フットプリント補完、グローバル整合性チェック | 確認済み（存在）／日本部分の充実度は未確認 |
| Microsoft Building Footprints | Microsoft | 北米・欧州・中南米・オセアニア中心、日本は主要対象外 | GeoJSON | https://atlas.co/data-sources/microsoft-building-footprints/ | ODbL | 対象外の可能性大、参考のみ | 推定（日本カバレッジ低い旨は複数の傍証、直接記載は未確認） |
| Google Open Buildings | Google | アフリカ・南アジア・東南アジア中心、日本対象外 | GeoJSON/CSV | https://gee-community-catalog.org/projects/global_buildings/ | CC BY 4.0 | 対象外 | 推定（同上） |
| OpenStreetMap Buildings（日本） | OSM コミュニティ | 全国、密度は地域依存 | GeoJSON/PBF等 | https://openstreetmap.jp/terms_and_privacy | ODbL、商用利用可だが**自治体データインポート由来分は個別許諾要確認** | フットプリント・POI補完、クロスチェック | 確認済み（ライセンス方針） |
| 国土数値情報 医療機関（P04） | 国交省 | 全国、直近版データ作成年度2020年度（要最新確認） | Shapefile/GML | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P04-v3_0.html | 「使用許諾条件を確認」の定型文言のみ確認、商用可否は個別要確認 | 医療機関ロケーション・重要施設判定 | 確認済み（存在）／商用可否は未確認 |
| 国土数値情報 福祉施設（P14） | 国交省 | 全国、2021年度版 | Shapefile/GML | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P14.html | 同上 | 福祉施設ロケーション | 確認済み（存在）／商用可否は未確認 |
| 国土数値情報 学校（P29） | 国交省 | 全国、2021年度版 | Shapefile/GML | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P29-v2_0.html | 同上 | 学校施設ロケーション | 確認済み（存在）／商用可否は未確認 |
| 国土数値情報 駅別乗降客数（S12） | 国交省 | 全国、2011年度以降毎年更新、直近は令和6年度版の存在確認 | GML/Shapefile | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v2_3.html | 同上（要確認） | 駅重要度（乗降客数）によるエリア重要度評価 | 確認済み（存在） |
| 大規模小売店舗立地法 届出情報 | 経産省→都道府県・市（分散） | 経産省一元公開は令和5年度末終了、以降は自治体個別公開 | CSV/Excel（自治体依存） | https://www.meti.go.jp/policy/economy/distribution/daikibo/todokede.html | 自治体によりCC BY 4.0等（大阪市・岡山市はCC BY 4.0確認） | 大規模小売店舗の位置・事業継続評価対象施設抽出 | 確認済み（一元公開終了の事実） |
| Wikidata POI | Wikimedia | 全世界 | RDF/API | https://wiki.openstreetmap.org/wiki/JA:Wikidata | CC0（商用利用可） | 施設名称・分類の補完 | 確認済み（ライセンス） |
| PLATEAU ユースケース uc22-009（高度な浸水シミュレーション） | 国交省/岡崎市 | 愛知県岡崎市（矢作川流域） | レポート・ツール | https://www.mlit.go.jp/plateau/use-case/uc22-009/ | PDL/CC BY相当 | 建物単位浸水深・全壊半壊リスク評価の先行事例として参照 | 確認済み（概要） |
| Project-PLATEAU/Disaster-damage-simulator | Project-PLATEAU | 全国利用可能（ArcGIS Pro向けツール） | ArcGIS Proツール | https://github.com/Project-PLATEAU/Disaster-damage-simulator | OSS | 家屋ごとの水害・土砂災害被害額予測ツール、本アプリのロジック参考 | 確認済み（存在） |

---

## PLATEAU属性の収録状況の詳細

### 確認できたこと（確認済み）
- CityGML標準のトップレベル属性として `storeysAboveGround`（地上階数）、`storeysBelowGround`（地下階数）、`bldg:usage`（用途）、`bldg:measuredHeight`（計測高さ、任意[0..1]）、`yearOfConstruction`（建築年、任意[0..1]、xs:gYear型）が定義されている（一次仕様書ページのタイトルから確認: `bldg:Building` 定義文書、`C.3.2.3 計測高さ` 定義文書）。
- `uro:BuildingDetailAttribute` には `totalFloorArea`（延床面積）、`buildingFootprintArea`（建築面積）、`buildingStructureType`（構造種別）、`siteArea`（敷地面積）などの拡張属性が定義されている（一次仕様書ページのタイトルから確認）。この属性群は都市計画基礎調査（建築確認申請番号等）に由来するとされる。
- `uro:RiverFloodingRiskAttribute`（河川浸水リスク属性）には浸水ランク（rankOrg：浸水深ランク）、浸水深（depth）、継続時間、規模などのフィールドがあることが確認できた。
- 洪水・津波・高潮・内水の4種の浸水想定区域情報がPLATEAUの災害リスク情報の枠組みに含まれることは、複数の可視化マニュアル・区の広報ページ（江戸川区・港区など）から確認できた。
- QGIS上で「災害リスク情報のテーブル結合」を行う手順記事（MIERUNE QGIS LAB）が存在することから、**災害リスク属性は建物本体に直接埋め込まれるケースと、別テーブル（浸水想定区域ポリゴン）を建物と空間結合して使うケースの両方が実務上あり得る**と推測される（未確認：どちらが東京23区の配布データの標準か）。

### 確認できなかったこと（未確認・要検証）
- **東京23区の配布データ（2020年度版・2022年度版）の建物に、実際に `uro:BuildingRiverFloodingRiskAttribute` 等の災害リスク属性が付与されているか、また何%の建物に収録されているか**は、WebSearchのスニペットからは判断できなかった。これは本アプリの一次スクリーニング精度を左右する最重要事項であり、**実データ（CityGMLファイル）をダウンロードして直接確認する必要がある**。
- 地下階数（storeysBelowGround）の「東京23区サンプルで欠損ゼロ」という情報は二次情報（Zenn個人技術記事、投稿者独自の分析）に基づくもので、一次資料（PLATEAU公式ドキュメント）では確認できていない。信頼度は中程度。
- 用途（bldg:usage）・住所の欠損率「約13%」も同じZenn記事由来であり、東京23区データ全体を代表する保証はない（記事は「エリアコード・住所フィールド」の欠損に言及、用途そのものの欠損率は明言されていない可能性がある＝要原文確認）。
- 川崎市・横浜市データに災害リスク属性が含まれるかは全く確認できていない。川崎市データセット名に「ジオデータベース（防災）」という表記があったことから、防災関連の別ファイルが用意されている可能性はあるが、内容は未確認。
- `uro:BuildingInlandFloodingRiskAttribute`（内水）、`uro:BuildingHighTideRiskAttribute`（高潮）、`uro:BuildingTsunamiRiskAttribute`（津波）、`uro:BuildingLandSlideRiskAttribute`（土砂災害）の各属性について、個別の定義ページ（`uro--BuildingXxxRiskAttribute.html`）は検索結果に直接ヒットせず、内容の詳細（フィールド構成）は未確認。`uro:ReservoirFloodingRiskAttribute`（ため池等）のページは存在確認できた。
- 収録は「浸水想定区域内の建物のみ」なのか「全建物に対して非該当時はnullまたは属性なし」なのかも未確認。一般的なPLATEAU仕様の考え方から、**浸水想定区域外の建物には当該リスク属性自体が付与されない設計である可能性が高い**（推定）。

---

## ツール評価

| ツール | 評価 | 根拠・コメント |
|---|---|---|
| PLATEAU GIS Converter | ◎ 最有力 | Rust製、GUI/CLIあり、CityGML→GeoPackage/3D Tiles/MVT/FlatGeobuf/Shapefile等に変換可能。属性の欠落なく変換できる設計が謳われている。パイプライン化しやすい。Project-PLATEAU公式版とMIERUNE版（先行・実験版）の2系統があるが機能はほぼ共通と見られる。 |
| plateau-qgis-plugin | ◎ 探索・検証フェーズで有用 | QGIS公式リポジトリ登録済み、属性付きでCityGMLを高速読込。要件定義段階での属性の目視確認・収録率のサンプリング調査に最適。 |
| PlateauKit（ozekik） | ○ Python自動処理に有力 | Jupyter対応のPlateauLabもあり、データ取得〜変換〜分析をコード化しやすい。バッチでの建物DB構築を想定するなら第一候補。 |
| plateaupy（AcculusSasao） | △ 補助的 | パーサ・3Dビューア用途が主で、属性の網羅的抽出には不向きな可能性。 |
| PlateauUtils（Project-PLATEAU公式） | △〜○ 要評価 | 公式提供だが情報が少なく、実運用実績の確認ができていない。 |
| GDAL（ogr2ogr / GMLASドライバ） | △ 汎用だが非推奨 | CityGMLの汎用対応は限定的（標準GMLドライバは基本的な読み込みのみ、GMLASはスキーマ駆動で複雑）。PLATEAU独自拡張（uroネームスペース）への完全対応は未確認であり、PLATEAU公式ツール（GIS Converter/QGISプラグイン）を優先すべき。 |
| PLATEAU SDK for Unity/Unreal | △ 本アプリには過剰 | ゲームエンジン向けでC# APIによる属性アクセスは可能だが、Webアプリやバッチ処理のバックエンドとして使うには不向き。3D可視化UIを作る場合は候補になり得る。 |
| Flateau（Pacific Spatial） | ○ 軽量代替として有力 | PLATEAU建物データをGeoPackage/GeoParquetの2D形式に事前変換済みで配布。211都市分をカバーしており、独自にCityGMLをパースする手間を省ける。ただし収録属性がPLATEAU全属性を含むか（特に災害リスク属性）は未確認、要検証。 |

---

## 未確認事項・要検証リスト（正直な申告）

WebFetchが使えない環境のため、以下は**一次資料の本文を直接読めておらず、検索結果のタイトル・スニペットからの推測にとどまる**：

1. **最重要**: 東京23区・目黒区・世田谷区・渋谷区・大田区・川崎市・横浜市の実データ（CityGMLファイル）に、`uro:BuildingRiverFloodingRiskAttribute` 等の災害リスク属性が実際にどの程度（何%の建物に）収録されているか。→ 実ファイルをダウンロードし、plateau-qgis-pluginかPLATEAU GIS Converterで開いて属性を直接サンプリング確認する必要がある。
2. 内水・高潮・津波・土砂災害の各リスク属性（`uro:BuildingInlandFloodingRiskAttribute`、`uro:BuildingHighTideRiskAttribute`、`uro:BuildingTsunamiRiskAttribute`、`uro:BuildingLandSlideRiskAttribute`）の正式なフィールド定義・単位・コード値。個別定義ページを直接読めていない。
3. 川崎市・横浜市の最新版データ年度（2022年度以降の更新があるか）。検索結果は2020・2022年度までしか確認できず、2023〜2025年度版の有無は未確認。
4. 東京都都市計画基礎調査の「建物現況調査」データが、区市町村単位・建物単位でオープンデータとして一般公開されているか（東京都オープンデータカタログで見つかったのは「土地利用現況調査GISデータ」のみで、「建物現況」の建物単位データセットの直接URLは特定できなかった）。取得には東京都都市整備局への個別申請が必要な可能性がある。
5. 国土数値情報（P04/P14/P29/S12）の商用利用可否。「使用許諾条件を確認すること」という定型的な注意書きしか確認できておらず、実際の利用規約本文（通常はCC BY相当が多いとされるが未確認）を読めていない。
6. PLATEAU GIS ConverterおよびPlateauKit等各ツールのライセンス条項（MIT等OSSライセンスの正式表記）。
7. 基盤地図情報「建築物外周線」に階数・用途などの属性が付随するか、それとも純粋にポリゴン形状のみか。
8. Overture Mapsの建物データセットにおける日本国内の実際のカバレッジ率・PLATEAU由来データの反映範囲。
9. uc22-009以外に、建物単位の「事業継続」（浸水による営業停止期間・機能停止）を直接評価したPLATEAUユースケースが他にあるか（`Disaster-damage-simulator`は被害額推定寄りで、営業停止期間の推定ロジックを持つかは未確認）。
10. 大規模小売店舗立地法データについて、目黒区・世田谷区・渋谷区・大田区・川崎市・横浜市を含む東京都・神奈川県の届出情報がオープンデータとして現在も入手可能か（東京都・神奈川県のポータルは直接検索していない）。

---

## 参照URL一覧

- [3D都市モデル（Project PLATEAU）東京都23区 - G空間情報センター](https://www.geospatial.jp/ckan/dataset/plateau-tokyo23ku)
- [3D都市モデル（Project PLATEAU）東京23区（2022年度）](https://wscart.geospatial.jp/ckan/dataset/plateau-tokyo23ku-2022)
- [Open Data | 3D都市モデルオープンデータ | PLATEAU](https://www.mlit.go.jp/plateau/open-data/)
- [PLATEAU 目黒区（2025年度）](https://www.geospatial.jp/ckan/dataset/plateau-13110-meguro-ku-2025)
- [PLATEAU 世田谷区（2023年度）](https://www.geospatial.jp/ckan/dataset/plateau-13112-setagaya-ku-2023)
- [PLATEAU 渋谷区（2025年度）](https://www.geospatial.jp/ckan/dataset/plateau-13113-shibuya-ku-2025)
- [PLATEAU 大田区（2023年度）](https://www.geospatial.jp/ckan/dataset/plateau-13111-ota-ku-2023)
- [PLATEAU 川崎市（2022年度）](https://www.geospatial.jp/ckan/dataset/plateau-14130-kawasaki-shi-2022)
- [PLATEAU 横浜市（2020年度）](https://www.geospatial.jp/ckan/dataset/plateau-14100-yokohama-city-2020)
- [Site Policy | PLATEAU](https://www.mlit.go.jp/plateau/site-policy/)
- [FAQ | PLATEAU](https://www.mlit.go.jp/plateau/faq/)
- [uro:BuildingDetailAttribute 定義](https://www.mlit.go.jp/plateaudocument01-01/Contents/%E5%AE%9A%E7%BE%A9%E6%96%87%E6%9B%B8/uro--BuildingDetailAttribute.html)
- [uro:ReservoirFloodingRiskAttribute 定義](https://www.mlit.go.jp/plateaudocument01-01/Contents/%E5%AE%9A%E7%BE%A9%E6%96%87%E6%9B%B8/uro--ReservoirFloodingRiskAttribute.html)
- [bldg:Building 定義](https://www.mlit.go.jp/plateaudocument01-02/contents/1/bldg_Building.html)
- [C.3.2.3 計測高さ（bldg:measuredHeight）](https://www.mlit.go.jp/plateaudocument02/tocC/tocC_03/tocC_03_02/tocC_03_02_03/)
- [高度な浸水シミュレーション | Use Case uc22-009](https://www.mlit.go.jp/plateau/use-case/uc22-009/)
- [3D都市モデルを活用した災害リスク情報の可視化マニュアル (PDF)](https://www.mlit.go.jp/plateau/file/libraries/doc/plateau_doc_0005_ver02.pdf)
- [QGISでPLATEAUデータを活用しよう〜災害リスク情報のテーブル結合・3D表示〜](https://qgis.mierune.co.jp/posts/usecase_plateau-data)
- [GitHub - Project-PLATEAU/PLATEAU-GIS-Converter](https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter)
- [GitHub - MIERUNE/plateau-gis-converter](https://github.com/MIERUNE/plateau-gis-converter)
- [PLATEAU GIS Converter サイト](https://project-plateau.github.io/PLATEAU-GIS-Converter/)
- [PLATEAU QGIS Plugin - QGIS公式プラグインリポジトリ](https://plugins.qgis.org/plugins/plateau_plugin/)
- [GitHub - Project-PLATEAU/plateau-qgis-plugin](https://github.com/Project-PLATEAU/plateau-qgis-plugin)
- [GitHub - AcculusSasao/plateaupy](https://github.com/AcculusSasao/plateaupy)
- [GitHub - Project-PLATEAU/PlateauUtils](https://github.com/Project-PLATEAU/PlateauUtils)
- [GitHub - ozekik/plateaukit](https://github.com/ozekik/plateaukit)
- [PlateauKit PyPI](https://pypi.org/project/plateaukit)
- [PlateauKit ライセンスページ](https://ozekik.github.io/plateaukit/license/)
- [GDAL GML driver ドキュメント](https://gdal.org/en/latest/drivers/vector/gml.html)
- [GDAL GMLAS driver ドキュメント](https://gdal.org/en/stable/drivers/vector/gmlas.html)
- [Flateau (Building footprint data in Japan) - source.coop](https://source.coop/pacificspatial/flateau)
- [GitHub - pacificspatial/flateau](https://github.com/pacificspatial/flateau)
- [Japan's Building Footprints - Tech Blog (Mark Litwintschik)](https://tech.marksblogg.com/building-footprints-japan.html)
- [東京都オープンデータカタログサイト - データセット一覧](https://catalog.data.metro.tokyo.lg.jp/dataset?organization=t000008)
- [土地利用現況調査GISデータ - 東京都オープンデータ](https://catalog.data.metro.tokyo.lg.jp/dataset/t000008d2000000019)
- [都市計画基礎調査実施要領（第５版）(PDF)](https://www.mlit.go.jp/toshi/tosiko/content/001617949.pdf)
- [都市計画基礎調査情報のオープン化に向けた取組 - 国交省](https://www.mlit.go.jp/toshi/city_plan/toshi_city_plan_tk_000049.html)
- [基盤地図情報サイト | 国土地理院](https://www.gsi.go.jp/kiban/)
- [ダウンロードできる基盤地図情報の種類 | 国土地理院](https://www.gsi.go.jp/kiban/syurui.html)
- [基盤地図情報ダウンロードサービス](https://service.gsi.go.jp/kiban/)
- [Overture Maps Buildings Guide](https://docs.overturemaps.org/guides/buildings/)
- [Overture Maps Attribution and Licensing](https://docs.overturemaps.org/attribution/)
- [Microsoft Building Footprints (atlas.co解説)](https://atlas.co/data-sources/microsoft-building-footprints/)
- [Global Google-Microsoft Open Buildings Dataset](https://gee-community-catalog.org/projects/global_buildings/)
- [ライセンスとプライバシーポリシーについて | OpenStreetMap Japan](https://openstreetmap.jp/terms_and_privacy)
- [利用可能なデータソース | OpenStreetMap Japan](https://openstreetmap.jp/node/764/)
- [JA:ODbL/License Transition/Guidance To Data Consumers - OSM Wiki](https://wiki.openstreetmap.org/wiki/JA:ODbL/License_Transition/Guidance_To_Data_Consumers)
- [国土数値情報 医療機関データ (P04)](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P04-v3_0.html)
- [国土数値情報 福祉施設データ (P14)](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P14.html)
- [国土数値情報 学校データ (P29)](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P29-v2_0.html)
- [国土数値情報 駅別乗降客数データ (S12)](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v2_3.html)
- [国土数値情報ダウンロードサイト](https://nlftp.mlit.go.jp/ksj/)
- [大規模小売店舗立地法（大店立地法）の届出状況について - METI](https://www.meti.go.jp/policy/economy/distribution/daikibo/todokede.html)
- [大店立地法新設届出情報 | 日本ショッピングセンター協会](https://www.jcsc.or.jp/sc_data/sc_open/daitenhou)
- [JA:Wikidata - OpenStreetMap Wiki](https://wiki.openstreetmap.org/wiki/JA:Wikidata)
- [JA:License/Use Cases - OpenStreetMap Wiki](https://wiki.openstreetmap.org/wiki/JA:License/Use_Cases)
- [GitHub - Project-PLATEAU/Disaster-damage-simulator](https://github.com/Project-PLATEAU/Disaster-damage-simulator)
- [GitHub - Project-PLATEAU/evacuation-simulation-tools](https://github.com/Project-PLATEAU/evacuation-simulation-tools)
- [【PLATEAU×Python】東京23区の建物DB構築（前編）— Zenn](https://zenn.dev/investaitech/articles/5712d0f0410e08)
- [【PLATEAU×Python】東京23区の建物DB構築（後編）— Zenn](https://zenn.dev/investaitech/articles/3c03d038c683ad)
- [3D都市モデル（Project PLATEAU） 属性情報公開リスト (PDF)](https://gic-plateau.s3.ap-northeast-1.amazonaws.com/2020/attributedata.pdf)
- [plateau-streaming-tutorial (3D Tiles配信)](https://github.com/Project-PLATEAU/plateau-streaming-tutorial/blob/main/3d-tiles/plateau-3dtiles-streaming.md)
