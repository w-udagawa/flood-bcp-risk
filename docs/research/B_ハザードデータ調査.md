# B. 浸水ハザード・浸水実績・リアルタイム水文データ調査

調査日: 2026-09-09（Claude調査、WebSearchのみ使用。WebFetch未使用のため、各URLの実データ・実レスポンスは未検証。すべてWebSearchのスニペット・要約に基づく二次情報）
対象地域第一候補: 東急線沿線（目黒区・世田谷区・渋谷区・大田区、川崎市・横浜市の一部）

---

## 要約（10行以内）

1. 洪水（外水）ハザードは国土数値情報A31・重ねるハザードマップ・不動産情報ライブラリAPIの3経路で全国一律に入手可能で、建物単位の一次スクリーニングに十分使える解像度（ポリゴン/50mメッシュ相当）がある。**確認済み度は高い。**
2. 内水（雨水出水）ハザードは国土数値情報A51が2024〜2025年度版で整備が進んでいるが、**東京都・神奈川県が収録対象に含まれているかは未確認**（要検証）。都独自の「浸水予想区域図」はGIS(Shape)形式で東京都オープンデータカタログから配信されており、こちらは対象区（目黒区・世田谷区・渋谷区・大田区含む城南地区河川流域等）をカバーしていると見られる。**PoCの内水評価はA51ではなく都のGISデータが主軸になる可能性が高い。**
3. 川崎市は内水ハザードマップ（浸水想定区域）をオープンデータとして公開（区版PDF中心、GIS化の有無は未確認）。横浜市は「わいわい防災マップ」でGIS閲覧可能だが、ダウンロード可能なオープンデータ形式かは未確認。
4. 重ねるハザードマップのタイル配信（disaportaldata.gsi.go.jp/raster/...）はXYZタイル・PNG形式で、洪水/内水/高潮/津波/家屋倒壊等氾濫想定区域の個別レイヤが揃い、出典表記のみで商用利用可（無料）。**建物単位判定には画素抽出（reverse geocoding的処理）が必要でやや実装コストがかかる。**
5. 2025年12月、国交省「不動産情報ライブラリ」がハザード系ポリゴンをXYZタイルAPIとして新規配信開始（洪水浸水想定・土砂災害警戒区域・津波・高潮・避難所の5種、内水は含まれない可能性）。APIキーは無料・即日〜5営業日で発行、商用利用可（出典明記条件あり）。**本アプリのバックエンドAPI選定において最有力候補。**
6. リアルタイム水文（水位・雨量）は東京都「水防災総合情報システム」「東京アメッシュ」、国交省「川の防災情報」が無料でWeb公開されているが、公式APIとしての契約フリーの機械可読データ提供は「水防災オープンデータ提供サービス」（河川情報センター、**有償契約**）が主。将来機能としては東京都サイトのスクレイピングか有償契約の二択になりそうで、無料の公式API化は未確認。
7. 電気設備浸水対策の基準として国交省・経産省「建築物における電気設備の浸水対策ガイドライン」（2020年6月）が確認済み、地下街等は「地下街等における浸水防止用設備整備のガイドライン」（2016年8月）と「地下空間における浸水対策ガイドライン」が該当。いずれも建物機能停止リスク評価のロジック（地下受変電設備×浸水深）の根拠として使える。
8. 2025年9月11日の豪雨は目黒区自由が丘周辺で内水氾濫が発生し、「フレル・ウィズ自由が丘」（東急ストア含む商業施設）が地下1階浸水→受変電設備・防災設備水没→全館停電→約3か月弱の長期休業（12月5日営業再開）に至った、**本アプリのユースケースを実証する具体事例**として報道多数・裏付け十分。
9. 大田区・品川区にはレベル5相当の緊急安全確保が発令されるなど、対象エリア全体で内水リスクが顕在化した実績あり。
10. **結論**: 建物単位の一次スクリーニングにおいて、外水は複数の公式APIで十分な解像度が取れる。内水はPoCエリア（東急線沿線）に限れば東京都のGIS配信（浸水予想区域図）と川崎市のオープンデータで足りる可能性が高いが、**データの実際のダウンロード可否・座標系・粒度は未検証であり、次工程で東京都オープンデータカタログの実ファイルを直接確認する必要がある**。

---

## データ一覧表

| データ名 | 提供元 | 対象範囲・年度 | 形式 | 取得URL | ライセンス・商用利用 | 本アプリでの用途 | 確からしさ |
|---|---|---|---|---|---|---|---|
| 洪水浸水想定区域データ（河川単位）A31 | 国土交通省（国土数値情報） | 全国、2025年度版が最新（計画規模/想定最大規模/浸水継続時間/家屋倒壊等氾濫想定区域の4区分含む） | JPGIS2.1(GML)/Shapefile | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31.html | CC BY 4.0、商用利用可 | 外水氾濫の一次スクリーニング（建物ポリゴンとの空間結合） | 確認済み（形式・区分・ライセンスはWebSearch要約で複数一致） |
| 洪水浸水想定区域（1次メッシュ単位）A31-v4 | 国土交通省（国土数値情報） | 全国、Version4.0（2022年度作成、以降更新） | GML/Shapefile、1次メッシュ（約80km四方相当のメッシュ単位で集約） | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v4_0.html | CC BY 4.0想定 | 広域粗いスクリーニング用途（建物単位には粒度不足の可能性） | 推定（河川単位版との解像度差は製品仕様書未確認） |
| 雨水出水（内水）浸水想定区域データ A51 | 国土交通省（国土数値情報） | 全国、2024/2025年度版（製品仕様書第2.0版 令和7年3月） | JPGIS2.1(GML)/Shapefile | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A51-2024.html | CC BY 4.0想定 | 内水氾濫の一次スクリーニング（本命だが収録対象都県が未確認） | **未確認**：東京都・神奈川県が収録対象自治体に含まれるか要検証 |
| 高潮浸水想定区域データ A49 | 国土交通省（国土数値情報） | 全国、2021-2022年度データ中心（製品仕様書第1.1〜1.2版） | JPGIS2.1(GML)/Shapefile | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A49-v1_1.html | CC BY 4.0（一部制限あり） | 沿岸部（大田区羽田等）の高潮リスク評価 | 確認済み |
| 津波浸水想定データ A40 | 国土交通省（国土数値情報） | 全国、製品仕様書第2.2版（令和6年3月）が最新、座標系JGD2011 | JPGIS2.1(GML)/Shapefile | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A40-v2_0.html | CC BY 4.0想定 | 対象エリア（東急線沿線）は津波リスク低いため優先度低 | 確認済み（座標系のみ） |
| 東京都 浸水予想区域図（城南地区河川流域ほか） | 東京都建設局河川部／下水道局計画調整部 | 東京都区部14区域（神田川流域、城南地区河川流域＝目黒川・渋谷川・古川・立会川・内川・呑川、隅田川・新河岸川流域、多摩川流域等）。港区・新宿区・品川区・目黒区・大田区・世田谷区・渋谷区・杉並区・三鷹市等をカバー。想定最大規模降雨（1時間153mm、24時間690mm） | PDF（区域図）＋GIS(Shape)、座標系は測地成果2011平面直角座標系第9系（東京都オープンデータカタログ記載） | https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d0000000029 https://www.kensetsu.metro.tokyo.lg.jp/river/chusho_seibi/panhulink/menu | 東京都オープンデータ利用規約（CC BY相当、商用利用可と推定） | **本アプリの内水評価の主力候補**。外水・内水の両方を表示 | 確認済み（データセットページ存在確認）／解像度・実ファイル形式は未検証 |
| 東京都 水害リスク情報システム（浸水実績図） | 東京都建設局 | 都内、令和6年3月29日運用開始。過去浸水実績のアニメーション表示・住所検索 | Webマップ（ダウンロード可の記述あり、GIS形式は未確認） | https://www.suigai-risk.metro.tokyo.lg.jp/shinsui/jisseki/main.html | 未確認 | 過去実績による「実際に浸水した建物」の裏付けデータ | 確認済み（サイト存在）／データ形式は未確認 |
| 目黒区 水害ハザードマップ | 目黒区 | 目黒区 | PDF中心 | https://www.city.meguro.tokyo.jp/bousai/bousaianzen/bousai/map.html | 未確認 | 参考（GIS配信の有無は未確認） | 推定 |
| 世田谷区 洪水・内水氾濫ハザードマップ | 世田谷区 | 世田谷区（多摩川洪水版、内水氾濫・中小河川洪水版） | PDF中心。ただし世田谷区は別途「GISオープンデータサイト」を保有 | https://www.city.setagaya.lg.jp/02049/606.html （ハザードマップ） https://www.city.setagaya.lg.jp/01000/5466.html （GISオープンデータ案内） | 区オープンデータ指針に基づく（詳細未確認） | 参考・将来のGIS取得候補 | 推定（GISオープンデータサイトに浸水レイヤが含まれるかは未確認） |
| 渋谷区 洪水ハザードマップ・浸水実績 | 渋谷区 | 渋谷区（神田川流域・渋谷川流域、東京都公表資料ベース） | PDF/多言語対応 | https://www.city.shibuya.tokyo.jp/bosai/bosai/bosai-manual-map/kozui_map.html | 未確認 | 参考 | 推定 |
| 大田区 防災ハザードマップ・浸水実績図 | 大田区 | 大田区（多摩川ハザードマップ、高潮ハザードマップ、中小河川・土砂災害・内水氾濫ハザードマップ、浸水実績図は昭和60年〜令和7年） | PDF（日本語/やさしい日本語/英中併記） | https://www.city.ota.tokyo.jp/seikatsu/chiiki/bousai/suigai/hazardmap.html https://www.city.ota.tokyo.jp/seikatsu/chiiki/bousai/suigai/shinsui.html | 未確認 | 参考・過去実績の裏付け | 推定（GIS形式配信は未確認） |
| 川崎市 内水ハザードマップ（浸水想定区域）オープンデータ | 川崎市上下水道局 | 川崎市7区（川崎区・幸区・中原区・高津区・宮前区・多摩区・麻生区）、想定条件 1時間153mm | オープンデータとして公開（形式未確認、PDF中心の可能性） | https://www.city.kawasaki.jp/800/page/0000133400.html | 未確認 | 川崎市エリアの内水評価 | 確認済み（「オープンデータ」ページの存在）／実データ形式は未検証 |
| 横浜市 浸水ハザードマップ（洪水・内水・高潮） | 横浜市 | 横浜市全域、想定最大規模（1時間153mm） | PDF中心、詳細版は「わいわい防災マップ」（行政地図情報提供システム）でGIS的に閲覧可 | https://www.city.yokohama.lg.jp/kurashi/machizukuri-kankyo/kasen-gesuido/gesuido/bousai/naisuihm.html | 未確認 | 横浜市エリアの内水評価（PoC優先度は東急線沿線区より低） | 推定（わいわい防災マップがダウンロード可能なオープンデータかは未確認） |
| 重ねるハザードマップ タイル配信（洪水・内水・高潮・津波・土砂・家屋倒壊等） | 国土地理院 ハザードマップポータルサイト | 全国、都道府県ごとの掲載状況にばらつきあり | ラスタタイル（PNG）、地理院タイルと同仕様のXYZ形式 | 例: https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin/{z}/{x}/{y}.png https://disaportaldata.gsi.go.jp/raster/01_flood_l2_kaokutoukai_hanran_data/{z}/{x}/{y}.png https://disaportaldata.gsi.go.jp/raster/01_flood_l2_kaokutoukai_kagan_data/{z}/{x}/{y}.png https://disaportaldata.gsi.go.jp/raster/04_tsunami_newlegend_data/{z}/{x}/{y}.png | 出典「ハザードマップポータルサイト」を明記すれば商用・非商用問わず利用可。無料 | 建物ジオコードでの浸水深階級の画素抽出、A31/A51と相互補完・クロスチェック | 確認済み（複数の技術ブログ・国交省資料で一致） |
| 内水（雨水出水）浸水想定区域タイル | 国土地理院 重ねるハザードマップ | 都道府県・市区町村ごとに掲載状況が異なる（掲載状況一覧ページあり） | ラスタタイル（PNG想定） | https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/naisui.html （掲載状況一覧） | 同上 | 内水掲載エリアの確認に使用 | **未確認**：東急線沿線区の内水レイヤ掲載有無は要検証（一覧ページを直接確認する必要あり） |
| 不動産情報ライブラリ 防災情報API（洪水浸水想定・土砂災害警戒区域・津波浸水想定・高潮浸水想定・避難場所 の5種、XKT系エンドポイント） | 国土交通省 不動産情報ライブラリ | 全国、2025年12月4日頃API配信開始（報道あり） | XYZタイルAPI（GeoJSON/PBF想定）、z=15で建物単位に近い粒度（1タイル約1-2km四方、記事では町丁目レベルと表現） | https://www.reinfolib.mlit.go.jp/help/apiManual/xkt002/ https://www.reinfolib.mlit.go.jp/api/request/ https://www.mlit.go.jp/report/press/tochi_fudousan_kensetsugyo17_hh_000001_00068.html | APIキー無料発行（申請後最短即日〜5営業日）、商用利用可（出典明記等の利用約款あり） | **建物単位スクリーニングのバックエンドAPI第一候補**（洪水・土砂・津波・高潮） | 確認済み（複数記事・国交省報道発表で裏付け）。**内水（雨水出水）が含まれるかは未確認** |
| 東京都 水防災総合情報システム | 東京都建設局 | 都内中小河川（神田川、隅田川ほか）雨量計・水位計・河川監視カメラ（5分ごと静止画） | Webサイト（リアルタイム表示）。機械可読API化は未確認 | https://www.kasen-suibo.metro.tokyo.lg.jp/ | 無料・利用規約未確認。API提供は未確認（スクレイピング前提の可能性） | 将来機能：リアルタイム水位・雨量のアラート表示 | 確認済み（サイト存在）／API有無は未確認 |
| 東京アメッシュ | 東京都下水道局（気象協会運営） | 東京都全域、降雨強度分布（画像ベース） | 画像配信（過去に非公式APIの解析事例あり）、公式API・利用規約の商用可否は未確認 | https://tokyo-ame2.jwa.or.jp/doc/ja/operation.html | **未確認**（商用利用規約の明記なし） | 将来機能：リアルタイム降雨強度の可視化 | 未確認 |
| 川の防災情報（river.go.jp） | 国土交通省 | 全国の河川水位・雨量 | Webポータル（PC/モバイル）、市区町村向け拡張版はID要 | https://www.river.go.jp/portal/ | 無料閲覧、API/データ配信は原則なし（水防災オープンデータ提供サービス経由が公式ルート） | 参考・将来のリアルタイム連携候補 | 確認済み（サイト存在） |
| 水防災オープンデータ提供サービス（河川情報数値データ配信事業） | 一般財団法人河川情報センター（国交省水管理・国土保全局所管事業） | 全国、レーダ雨量（XRAIN含む）・水位・雨量テレメータ・河川カメラ画像等 | 数値データ配信（契約約款あり） | https://www.river.or.jp/koeki/opendata/index.html https://www.river.or.jp/koeki/opendata/data/04_suuchi_yakkan_v7.pdf | **有償契約**（実費相当額）。契約約款あり | 将来のリアルタイム機能（本格運用フェーズ向け、PoCでは非採用が妥当） | 確認済み |
| 気象庁 高解像度降水ナウキャスト | 気象庁（配信は気象業務支援センター経由） | 全国、250mメッシュ、5〜10分ごと更新 | XML電文/GRIB2等、気象業務支援センター経由の配信が主（直接無料APIは限定的） | https://www.jmbsc.or.jp/jp/online/file/f-online30300.html | 気象業務支援センター経由は有償の可能性。気象庁本体サイトの可視化は無料閲覧のみ | 将来機能：直近降雨予測によるリアルタイムリスク表示 | 未確認（無料での機械可読データ取得経路が不明瞭） |
| 建築物における電気設備の浸水対策ガイドライン | 国土交通省住宅局建築指導課／経済産業省産業保安グループ電力安全課 | 全国（高圧受変電設備を有する建築物） | PDF | https://www.mlit.go.jp/jutakukentiku/build/content/001349327.pdf | 公的資料、二次利用可能（詳細規約未確認） | 建物機能停止リスクの判定ロジック（地下受変電設備×想定浸水深）の根拠 | 確認済み（2020年6月公表、川崎市の高層マンション事例が策定契機と明記） |
| 地下街等における浸水防止用設備整備のガイドライン | 国土交通省 水管理・国土保全局 河川環境課 水防企画室 | 全国（地下街・地下鉄駅・地下売場等） | PDF（平成28年8月） | https://www.mlit.go.jp/common/001142793.pdf | 公的資料 | 地下空間を持つ建物の追加リスク評価 | 確認済み |
| 地下空間における浸水対策ガイドライン（解説） | 国土交通省 水管理・国土保全局 | 全国 | PDF | https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/chika/pdf/honpen.pdf | 公的資料 | 同上 | 確認済み |

---

## タイルURL・API仕様の詳細

### 1. 国土地理院 重ねるハザードマップ（disaportaldata.gsi.go.jp）
- 地理院タイルと同仕様のXYZ形式ラスタタイル（PNG）。都道府県・市区町村単位で掲載状況にばらつきがあり、「オープンデータ配信」ページに一覧表がある（`https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/opendata.html`）。
- 確認できた具体タイルURLパターン例（WebSearch要約ベース、実アクセス未検証）：
  - 洪水浸水想定区域（想定最大規模）: `https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin/{z}/{x}/{y}.png`
  - 家屋倒壊等氾濫想定区域（氾濫流）: `https://disaportaldata.gsi.go.jp/raster/01_flood_l2_kaokutoukai_hanran_data/{z}/{x}/{y}.png`
  - 家屋倒壊等氾濫想定区域（河岸侵食）: `https://disaportaldata.gsi.go.jp/raster/01_flood_l2_kaokutoukai_kagan_data/{z}/{x}/{y}.png`
  - 土砂災害警戒区域（急傾斜地）: `https://disaportaldata.gsi.go.jp/raster/05_kyukeishakeikaikuiki/{z}/{x}/{y}.png`
  - 津波浸水想定（新配色）: `https://disaportaldata.gsi.go.jp/raster/04_tsunami_newlegend_data/{z}/{x}/{y}.png`
  - **内水（雨水出水）浸水想定区域・高潮浸水想定区域の正確なパス文字列はWebSearchでは確認できず**（`naisui.html`「掲載状況一覧」ページに記載があるはずだが未取得）→要検証。
- ズームレベル: 「災害リスク情報を縮尺に応じてタイルに分割した、地理院タイルと同仕様」との記述のみで、正確な対応レベル（例: z=2〜17）はWebSearchでは特定できず。地理院タイル自体はz=2〜18が一般的。**要検証**。
- 浸水深の色分け基準（洪水ハザードマップ作成の手引き・水害ハザードマップ作成の手引きより）：
  - 境界値は 0.5m／3.0m（標準）、必要に応じ 5.0m を追加。10m・20mも使用（津波等）。
  - 0.5m未満＝1階床上浸水未満相当、0.5〜3.0m＝1階水没相当（1階天井～2階床下）、3.0〜5.0m＝2階天井付近まで、5.0m以上＝2階水没。
  - **実際のPNGカラーコード（RGB値）→浸水深階級の対応表はWebSearchでは取得できず**。国交省「水害ハザードマップ作成の手引き」PDF内に記載がある可能性が高い→要検証（直接PDF確認が必要）。
- 利用規約: 「出典：ハザードマップポータルサイト」の明記で商用・非商用問わず利用可（加工した場合はその旨明記）。ただし、ため池決壊・一部都道府県の津波浸水想定、液状化関連レイヤはオープンデータ対象外の例外あり。

### 2. 不動産情報ライブラリ（reinfolib）防災情報API
- 2025年12月、国交省が新たに5種類の防災情報をAPI配信開始（洪水浸水想定区域＝想定最大規模、土砂災害警戒区域、津波浸水想定、高潮浸水想定区域、指定緊急避難場所）と報道されている（built.itmedia.co.jp記事、国交省報道発表）。
- 配信形式: XYZタイルクエリ方式（緯度経度→タイル座標変換が必要）。技術ブログ（zenn.dev/sktt_panda）ではPythonでのWeb Mercator変換・GeoJSON交差判定の実装例が紹介されている。
- 洪水データのエンドポイント例として `XKT002`（ヘルプページ `https://www.reinfolib.mlit.go.jp/help/apiManual/xkt002/` の存在を確認）。z=15で1タイルあたり約1〜2km四方、町丁目レベルの粒度との言及あり（建物単位判定には周辺ポリゴンとの交差判定実装が必要）。
- **内水（雨水出水）浸水想定区域がAPI対象5種に含まれるかは確認できず**（報道では「洪水浸水想定区域」表記のみ、内水は別枠の可能性）→要検証。
- APIキー取得: 利用規約同意の上、API利用申請フォームから申請。無料。最短即日〜5営業日で発行。
- 利用規約: 商用利用可だが出典記載の文言が明確に指定されている（詳細な文言はWebSearchでは未取得、`https://www.reinfolib.mlit.go.jp/help/termsOfUse/` を直接確認する必要あり）。

### 3. 国土数値情報（A31/A51/A49/A40）
- ダウンロードサイト: `https://nlftp.mlit.go.jp/ksj/`（都道府県・年度を選択してGML/Shapefileをダウンロード、APIではなく静的ファイル配信）。
- ライセンス: CC BY 4.0（商用利用可）だが、A49（高潮）は「一部制限あり」との記載を確認。
- 座標系: 少なくともA40（津波）はJGD2011（世界測地系）緯度経度。他データセットも同様と推定。
- A31の区分: 計画規模／想定最大規模／浸水継続時間／家屋倒壊等氾濫想定区域（氾濫流・河岸侵食）の4種類の属性・図郭が用意されている。
- A31-v4（1次メッシュ単位版）は河川単位版より広域集約されたメッシュデータで、Version 4.0は2022年度作成。河川単位版（ポリゴン、詳細）との解像度差の詳細な説明はWebSearchでは未取得→製品仕様書PDF直接確認が必要。

### 4. 東京都 浸水予想区域図・水害リスク情報システム
- 東京都オープンデータカタログ: `https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d0000000029`（「浸水予想区域図」データセット）。GIS(Shape)形式、座標系は測地成果2011の平面直角座標系第9系との記述あり。
- 城南地区河川流域（目黒川・渋谷川・古川・立会川・内川・呑川）の浸水予想区域図QAが `https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000067071` にあり、想定最大規模降雨（1時間153mm、24時間690mm）に基づく。対象自治体は港区・新宿区・品川区・目黒区・大田区・世田谷区・渋谷区・杉並区・三鷹市。
- 内水（下水道能力超過）は下水道局が別途「雨水出水浸水想定区域図」も公表（`https://www.gesui.metro.tokyo.lg.jp/living/amesh/inundation/jonanusui`）。
- 水害リスク情報システム（令和6年3月運用開始）: `https://www.suigai-risk.metro.tokyo.lg.jp/shinsui/jisseki/main.html` で過去浸水実績のアニメーション表示・住所検索が可能。ダウンロード可否・形式は未確認。

### 5. 水位・雨量リアルタイム系
- 東京都 水防災総合情報システム: `https://www.kasen-suibo.metro.tokyo.lg.jp/` — 雨量計・水位計の観測情報、河川監視カメラ（5分間隔静止画）をリアルタイム提供。機械可読API・利用規約の商用可否は未確認。
- 水防災オープンデータ提供サービス: 河川情報センター（`www.river.or.jp`）が有償配信。XRAIN・Cバンドレーダ雨量、テレメータ（雨量・水位）、河川カメラ画像を数値データとして配信。契約約款PDFあり（`04_suuchi_yakkan_v7.pdf`）。**PoCでは非採用、本格運用フェーズでの検討事項**。
- 気象庁 高解像度降水ナウキャスト: 250mメッシュ・高頻度更新。気象業務支援センター経由の配信が主で、無料での直接機械可読データ取得経路は不明瞭（要検証）。

---

## 2025年9月11日 豪雨の公開情報まとめ（事実のみ、出典付き）

- 2025年9月11日、東京都心・神奈川県では14時ごろから1時間に100mmを超える雨が相次ぎ、気象庁は「記録的短時間大雨情報」を複数回発表した。〔[tenki.jp](https://tenki.jp/forecaster/deskpart/2025/09/11/35673.html)〕
- 大田区・品川区にレベル5相当の「緊急安全確保」が発令された。〔[tenki.jp](https://tenki.jp/forecaster/deskpart/2025/09/11/35673.html)〕
- NHK報道では、目黒区自由が丘周辺で内水氾濫（地形的に「鍋の底」状の低地、暗渠化された「見えない川」が溢れる現象）が発生したと専門家解説とともに報じられている。〔[NHK首都圏](https://news.web.nhk/shutoken/articles/101/027/35/)〕
- 東京新聞は、自由が丘の商業ビルで豪雨後に「全館停電」が長引いたこと、品川区戸越銀座の道路冠水、今後も下水処理能力を上回る豪雨が起こりうるという都市の脆弱性を報じた。〔[東京新聞デジタル](https://www.tokyo-np.co.jp/article/440444)〕
- 自由が丘の商業施設「フレル・ウィズ自由が丘」（東急ストア運営）は、9月11日の局地的豪雨により地下1階が浸水し、地下設置の受変電設備・防災設備が水没、建物全体の電力供給が停止したため、食品スーパー「東急ストア」・雑貨店「Standard Products」など全テナントが休業に追い込まれた。〔[東急ストア公式PDF 2025年9月16日付](https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20250916fullel.pdf)〕
- 復旧は長期化し、東急ストア公式発表（2025年10月10日・11月21日付）で進捗報告が継続的に出され、2025年12月5日に営業再開予定と報じられた（約3か月弱の全館休業）。〔[号外NET目黒区 2025年11月29日](https://meguro.goguynet.jp/2025/11/29/fullelwith_jiyugaoka6/)〕〔[Yahoo!ニュース](https://article.yahoo.co.jp/detail/5f1af377907de70dc27bc5e0af1d3faeb9165f98)〕
- SNS（自由が丘.net/X）でも、自由が丘が「7年ぶりに浸水」、大井町線が一時運休、「トレインチ」やフレル・ウィズ周辺の1階・地下店舗の被害が大きかった旨の同時多発的な現地報告がある。〔[自由が丘.net (X)](https://x.com/jiyugaoka_net/status/1966108509424251041)〕
- テレビ朝日系（ANN）は自由が丘の浸水被害の実店舗映像とともに「本当の恐怖」という店主コメントを報道。〔[テレ朝NEWS/Yahoo!ニュース](https://news.yahoo.co.jp/articles/f7146313a2d36ddd0ceb5cca35d32295ed81de60)〕

**この事例は、本アプリが検出しようとする「浸水→地下受変電設備水没→建物機能・事業継続の長期停止」パターンの典型的な実証事例であり、要件定義のユースケース記述にそのまま使用できる。**

---

## 未確認事項・要検証リスト

1. 国土数値情報A51（雨水出水/内水）の2025年度版に東京都・神奈川県の市区町村が実際に収録されているか（対象自治体リストを製品仕様書またはダウンロードページで直接確認する必要あり）。
2. 重ねるハザードマップの「内水（雨水出水）浸水想定区域」タイルの正確なURLパス文字列、および目黒区・世田谷区・渋谷区・大田区・川崎市・横浜市がこのレイヤに掲載されているか（`naisui.html`掲載状況一覧の直接確認が必要）。
3. 重ねるハザードマップタイルの正確なズームレベル範囲（z最小・最大）と、各レイヤ（洪水/内水/高潮/津波/浸水継続時間/家屋倒壊）ごとのURLパスの一覧を網羅的に確認できていない。
4. 重ねるハザードマップPNGの色（RGB値）→浸水深階級の正確な対応表（凡例）。「水害ハザードマップ作成の手引き」PDF等の直接確認が必要。
5. 不動産情報ライブラリAPI（reinfolib）の防災情報5種に「内水（雨水出水）浸水想定区域」が含まれるか、正確なエンドポイント一覧（XKT002〜XKT00X）、リクエスト仕様・レスポンス形式（GeoJSON/PBF/MVT等）、レート制限。
6. 東京都オープンデータカタログの「浸水予想区域図」データセットの実ファイル形式（Shapefile/GeoJSON等）、実際の属性項目（浸水深区分、対象降雨条件等）、更新頻度、ライセンス条文の詳細。
7. 目黒区・世田谷区・渋谷区・大田区が独自にGIS形式（Shape/GeoJSON）で浸水ハザード・浸水実績データを公開しているか（区公式サイトはPDF中心の様子だが、オープンデータポータルの個別確認が必要。特に世田谷区の「GISオープンデータサイト」に浸水系レイヤが含まれるか）。
8. 川崎市上下水道局の内水ハザードマップ「オープンデータ」ページの実際の配信形式（PDFのみか、Shapefile/GeoJSONも含むか）。
9. 横浜市「わいわい防災マップ（行政地図情報提供システム）」がダウンロード可能なオープンデータ（GIS形式）を提供しているか、それとも閲覧専用のWebGISか。
10. 東京都水防災総合情報システム・東京アメッシュについて、機械可読な公式API（JSON/XML等）が無償で提供されているか、または画像スクレイピングが前提になるか。利用規約上の商用利用可否。
11. 気象庁高解像度降水ナウキャストのXML電文について、気象業務支援センターを介さない無償の直接取得経路（気象庁防災情報XMLフォーマット等）が存在するか。
12. 東京都水害リスク情報システム（浸水実績図）がGISダウンロード（Shapefile等）に対応しているか、Web地図閲覧のみか。
13. 国土数値情報A31-v4（1次メッシュ）とA31（河川単位）の解像度差・使い分けの詳細（製品仕様書PDFの直接確認が必要）。

---

## 参照URL一覧

### 国土数値情報（A31/A51/A49/A40）
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31.html
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v2_2.html
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v4_0.html
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31b-2023.html
- https://nlftp.mlit.go.jp/ksj/gml/product_spec/KS-PS-A31a-v4_2.pdf
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A51-2024.html
- https://nlftp.mlit.go.jp/ksj/gml/product_spec/KS-PS-A51-v2_0.pdf
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A49-v1_1.html
- https://nlftp.mlit.go.jp/ksj/gml/product_spec/KS-PS-A49-v1_2.pdf
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A40-v2_0.html
- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A40.html
- https://nlftp.mlit.go.jp/ksj/gml/product_spec/KS-PS-A40-v2_2.pdf
- https://nlftp.mlit.go.jp/ksj/
- https://www.mlit.go.jp/report/press/tochi_fudousan_kensetsugyo17_hh_000001_00061.html
- https://www.geospatial.jp/ckan/dataset/ksj-a31-83
- https://www.geospatial.jp/ckan/dataset/ksj-a40

### 東京都
- https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d0000000029
- https://portal.data.metro.tokyo.lg.jp/
- https://www.kensetsu.metro.tokyo.lg.jp/river/chusho_seibi/panhulink/menu
- https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000067071
- https://www.gesui.metro.tokyo.lg.jp/living/amesh/inundation/jonanusui
- https://www.gesui.metro.tokyo.lg.jp/living/amesh/inundation
- https://www.suigai-risk.metro.tokyo.lg.jp/shinsui/jisseki/main.html
- https://www.suigai-risk.metro.tokyo.lg.jp/shiryoshu/shinsui-kensaku/
- https://www.kensetsu.metro.tokyo.lg.jp/river/chusho_seibi/panhulink/kako
- https://www.kensetsu.metro.tokyo.lg.jp/river/chusho_seibi/panhulink/hazardmap
- https://www.kasen-suibo.metro.tokyo.lg.jp/
- https://tokyo-ame2.jwa.or.jp/doc/ja/operation.html
- https://www.gesui.metro.tokyo.lg.jp/about/aboutus/contents02/04
- https://www.bousai.metro.tokyo.lg.jp/link/1000045/1006156.html

### 区市（目黒・世田谷・渋谷・大田・川崎・横浜）
- https://www.city.meguro.tokyo.jp/bousai/bousaianzen/bousai/map.html
- https://www.city.setagaya.lg.jp/02049/606.html
- https://www.city.setagaya.lg.jp/01000/5466.html
- https://www.city.setagaya.lg.jp/02049/592.html
- https://www.city.shibuya.tokyo.jp/bosai/bosai/bosai-manual-map/kozui_map.html
- https://www.city.ota.tokyo.jp/seikatsu/chiiki/bousai/suigai/hazardmap.html
- https://www.city.ota.tokyo.jp/seikatsu/chiiki/bousai/suigai/shinsui.html
- https://www.city.kawasaki.jp/800/page/0000133400.html
- https://www.city.kawasaki.jp/800/page/0000125074.html
- https://www.city.kawasaki.jp/800/page/0000125083.html
- https://www.city.yokohama.lg.jp/kurashi/machizukuri-kankyo/kasen-gesuido/gesuido/bousai/naisuihm.html
- https://www.city.yokohama.lg.jp/bousai-kyukyu-bohan/bousai-saigai/map/shinsui/sinsuiHM.html

### 国土地理院 ハザードマップポータル
- https://disaportal.gsi.go.jp/
- https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/opendata.html
- https://disaportal.gsi.go.jp/hazardmap/copyright/opendata.html
- https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/naisui.html
- https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/copyright_data.html
- https://disaportal.gsi.go.jp/hazardmap/copyright/copyright.html
- https://disaportal.gsi.go.jp/hazardmap/copyright/katsuyoujireisyuu.pdf
- https://disaportal.gsi.go.jp/hazardmap/pamphlet/sousa2.pdf
- https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/pamphlet/sousa2.pdf
- https://disaportal.gsi.go.jp/hazardmapportal/hazardmap/copyright/pamphlet_opendata.pdf
- https://zenn.dev/byteinsight/articles/57bd27506c6572（重ねるハザードマップタイル活用の技術記事）
- https://sorabatake.jp/11283/（Tellus経由のマイ防災マップ作成解説）

### 不動産情報ライブラリ（reinfolib）
- https://www.reinfolib.mlit.go.jp/help/termsOfUse/
- https://www.reinfolib.mlit.go.jp/api/request/
- https://www.reinfolib.mlit.go.jp/help/apiManual/
- https://www.reinfolib.mlit.go.jp/help/apiManual/xkt002/
- https://www.mlit.go.jp/report/press/tochi_fudousan_kensetsugyo17_hh_000001_00068.html
- https://built.itmedia.co.jp/bt/articles/2512/04/news074.html
- https://zenn.dev/sktt_panda/articles/reinfolib-tile-api-python
- https://zenn.dev/sktt_panda/articles/japan-public-api-license-check
- https://digital-construction.jp/administration/2815

### リアルタイム水文・気象
- https://www.river.go.jp/portal/
- https://www.river.or.jp/koeki/opendata/index.html
- https://www.river.or.jp/koeki/opendata/data/04_suuchi_yakkan_v7.pdf
- https://www.mlit.go.jp/river/event/main/datahaishin/index.html
- https://suiboumap.gsi.go.jp/pdf/Data-riyo_manual.pdf（浸水ナビAPI仕様書、参考）
- https://www.jmbsc.or.jp/jp/online/file/f-online30300.html
- https://www.jma.go.jp/jma/kishou/know/kurashi/highres_nowcast.html

### 電気設備・地下空間ガイドライン
- https://www.mlit.go.jp/jutakukentiku/build/content/001349327.pdf（建築物における電気設備の浸水対策ガイドライン、2020年6月）
- https://www.meti.go.jp/press/2020/06/20200619003/20200619003.html
- https://www.mlit.go.jp/common/001142793.pdf（地下街等における浸水防止用設備整備のガイドライン、2016年8月）
- https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/chika/pdf/honpen.pdf（地下空間における浸水対策ガイドライン 解説）
- https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/hazardmap/pdf/hm_kaitei.pdf（洪水ハザードマップ作成の手引き）
- https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/hazardmap/suigai_hazardmap_tebiki_201604.pdf（水害ハザードマップ作成の手引き）

### 2025年9月11日豪雨・自由が丘関連
- https://tenki.jp/forecaster/deskpart/2025/09/11/35673.html
- https://news.web.nhk/shutoken/articles/101/027/35/
- https://www.tokyo-np.co.jp/article/440444
- https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20250916fullel.pdf
- https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20251010fullel.pdf
- https://www.fullel.com/uploads/pdfs/fullel/000045/000045/d8272a17.pdf
- https://www.fullel.com/jiyugaoka/eventnews/detail/?cd=000130
- https://meguro.goguynet.jp/2025/11/29/fullelwith_jiyugaoka6/
- https://meguro.goguynet.jp/2025/10/02/fullelwith_jiyugaoka5/
- https://article.yahoo.co.jp/detail/5f1af377907de70dc27bc5e0af1d3faeb9165f98
- https://news.yahoo.co.jp/articles/f7146313a2d36ddd0ceb5cca35d32295ed81de60
- https://news.yahoo.co.jp/articles/b997bcdc3c59476e3994962f1f4483610f7d28ee
- https://x.com/jiyugaoka_net/status/1966108509424251041
- https://www.tvac.or.jp/news/51090（ボラ市民ウェブ、被害報告第3報）

---

## 調査手法についての注記

本調査はWebSearchツールのみを使用（環境制約によりWebFetchでの直接URL取得は未実施）。全ての情報はWebSearchが返す検索結果スニペット・自動要約に基づく二次情報であり、実際のAPIレスポンス・ファイル内容・利用規約全文は未検証。要件定義・実装計画に進む前に、上記「未確認事項・要検証リスト」の各項目について、WebFetch等が使える環境または人手でのURL直接確認を推奨する。検索は日本語29クエリを実施（英語検索は日本語クエリ内で十分な情報が得られたため、追加の英語専用検索は実施せず。国内公的機関のデータのため日本語ソースが一次情報として適切と判断）。
