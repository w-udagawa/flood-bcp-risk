# 浸水時建物機能停止リスク：被災事例・競合・ガイドライン調査（D）

調査日：2026-09-09　調査方法：WebSearch のみ（日英複数キーワード、30回以上実施）
※本調査は検索結果の要約に基づく。一次資料（PDF本文等）は未取得のため、数値・固有名詞は再確認を推奨（「要検証」参照）。

---

## 要約（結論）

1. **地下・低層に集中する脆弱設備（受変電設備・自家発電機・排水ポンプ・中央監視盤）が浸水すると、建物全体が長期停止する**ことが武蔵小杉（2019）、自由が丘フレル・ウィズ（2025、休業約3ヶ月弱）、千葉豪雨・山王病院/千葉大病院（2026）など複数事例で一貫して確認できた。**確認済み事実**。
2. 国交省「電気設備の浸水対策ガイドライン」(2020/6) は武蔵小杉事故を直接の契機とし、受変電設備等を「想定浸水深より高い位置」に置くことを推奨する構造。定量閾値（0.5m/3m等）は検索結果からは特定できず、原本PDF確認が必要（**要検証**）。
3. 東京都は豪雨対策目標降雨を時間75mm（区部）→ 気候変動対応で85mmへ引き上げ改定（2023年12月改定）。地下空間ガイドラインも2025年9月に改定されたばかり（**確認済み**、直近）。
4. 宅建業法改正（2020年8月施行）で水害ハザードマップの重要事項説明が義務化済み、浸水被害防止区域制度（特定都市河川法改正、2021年）も存在し、**法規制インフラは既に整備されている** → 本アプリはこれらを補完・高度化する位置づけになりうる。
5. 既存の建物単位フラッド評価サービスは海外（First Street/Flood Factor、JBA、Fathom、Munich Re LRI）で先行し、地点・建物フットプリント単位のスコアリングが実用化済み。**日本では建物単位×地下設備考慮のスクリーニングサービスは確認できず、差別化余地あり**（推測要素含む、後述）。
6. RisKmaは自治体・企業向けリアルタイム浸水予測で初期費用200万〜1000万円/月10〜30万円という価格情報あり。個人・中小事業者向けの安価な建物単位一次スクリーニングは競合が薄い可能性。
7. 治水経済調査マニュアル・水害の被害指標分析の手引に、浸水深別家屋被害率・事業所営業停止日数の算定式（延床面積×資産評価額×被害率、営業停止日数含む）が存在し、スコアリングロジックの参考になる。
8. JIS A 4716（浸水防止用設備建具型、2019年11月制定）が止水板等の性能等級の公的基準として存在。
9. ハザードマップ公開が不動産価格に与える影響は「限定的」との見方が多いが、風評被害・トラブルの実例は存在し、免責表記の設計が必要。
10. 会計検査院が災害拠点病院の自家発電機浸水対策不備を複数年度にわたり指摘しており、公的病院でも対策未了施設が現存する（**確認済み**、令和元年度・令和2年度報告）。

---

## 1. 被災事例一覧表

| 日付 | 施設 | 種別 | 浸水した設備・設置階 | 停止期間 | 出典 |
|---|---|---|---|---|---|
| 2019/10/12 台風19号 | パークシティ武蔵小杉ステーションフォレストタワー（川崎市） | タワーマンション（47階建） | 地下3階の高圧受変電設備等が浸水（山王排水樋管からの内水氾濫） | 電気復旧まで約17日（10/29）、生活正常化まで約1ヶ月、建物によっては1〜3ヶ月との説明も | [日経クロステック](https://xtech.nikkei.com/atcl/nxt/column/18/00154/00858/), [東京新聞](https://www.tokyo-np.co.jp/article/60914) |
| 2019/10/12-13 台風19号 | 川崎市市民ミュージアム | 博物館・収蔵庫 | 地下収蔵庫（約5,898㎡）に推定16万㎥浸水、約23万点の収蔵品被災 | 復旧・修復に「10年ほど」の見通し（原状回復不可能なものも多数） | [日経](https://www.nikkei.com/article/DGXMZO53008260V01C19A2L82000/), [美術手帖](https://bijutsutecho.com/magazine/news/headline/21286) |
| 2025/9/11 局地的豪雨（目黒区で最大1時間134mm） | フレル・ウィズ自由が丘（東急ストア運営の商業施設、自由が丘） | 商業施設 | 地下1階が浸水、地下設置の受変電設備・防災設備が浸水し全館停電 | 9/16休業発表、10月・11月時点で復旧未了、12/5全館営業再開（約3ヶ月弱の休業） | [東急ストアお知らせ](https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20250916fullel.pdf), [東京新聞](https://www.tokyo-np.co.jp/article/440444), [号外NET目黒区](https://meguro.goguynet.jp/2025/10/02/fullelwith_jiyugaoka5/) |
| 2026/8/13-14 千葉豪雨 | 千葉大学医学部附属病院 | 病院 | 地下設備浸水（排水管・基板等が冠水）、医療器具の洗浄・滅菌不能 | 8/19予定の手術全件中止、完全復旧まで「半年」見通し | [m3.com](https://www.m3.com/news/open/iryoishin/1353493) |
| 2026/8/13-14 千葉豪雨 | 山王病院（千葉市稲毛区） | 病院 | 地下の電気設備・非常用発電設備が水没、全診療科休診 | 入院患者約130人をDMAT協力で他院転院。2週間後（8/27）も再開未了 | [日経クロステック](https://xtech.nikkei.com/atcl/nxt/column/18/00154/02908/), [Yahooニュース(毎日新聞)](https://news.yahoo.co.jp/articles/e45724e3d399d229d8740ad13a0f60e07492f538) |
| 2026/8/13-14 千葉豪雨 | 千葉県内 高齢者施設257／医療施設53（総数） | 施設全般 | 詳細不明（同上記事内で言及） | 2週間経過後も多くが再開未了 | 同上（毎日新聞経由Yahoo） |
| 2004/10/9 台風22号 | 東京メトロ麻布十番駅 | 地下鉄駅 | 地下3階ホームが浸水（3番出入口からの流入、古川氾濫） | 南北線一時全線運転見合わせ（時間単位、詳細な日数は未確認） | [東京メトロ提供資料](https://www.kensetsu-plaza.com/kiji/post/22019), [Wikipedia](https://ja.wikipedia.org/wiki/%E9%BA%BB%E5%B8%83%E5%8D%81%E7%95%AA%E9%A7%85) |
| 2000年 台風/豪雨 | 名古屋市営地下鉄 | 地下鉄 | 検索結果内言及のみ（詳細未確認） | 最大2日間の運行停止、約47万人に影響（検索結果要約） | 国交省資料経由の要約（**要一次資料確認**） |
| 2012/10/29 ハリケーン・サンディ | Bellevue Hospital（NYC） | 病院 | 地下浸水、電力喪失 | 患者約500人を避難・転院 | [Fox News](https://www.foxnews.com/us/efforts-to-defend-nyc-hospitals-against-flood-break-down-in-sandys-torrent) |
| 2012/10/29 ハリケーン・サンディ | 75 Broad St / 33 Whitehall St（NYCデータセンター群、Internap, Peer1, Datagram等） | データセンター | 地下の燃料ポンプ・配電設備浸水、非常用発電機の燃料補給不能 | 数日間サービス停止（Gawker, HuffPost, BuzzFeed等がダウン） | [Data Center Knowledge](https://www.datacenterknowledge.com/business/massive-flooding-damages-several-nyc-data-centers) |
| 2017/8月 ハリケーン・ハービー | Ben Taub Hospital（ヒューストン） | 病院 | 地下浸水・下水逆流、薬局・給食部門等に影響 | 避難検討したが実施せず、浸水減少後に業務再開（詳細日数未確認） | [CBS News](https://www.cbsnews.com/amp/news/flooding-disrupts-care-at-houston-hospital-cancer-center) |
| 2001年 トロピカルストーム・アリソン（参考／教訓事例） | Memorial Hermann Hospital（ヒューストン） | 病院 | 地下の非常用発電機が浸水し機能喪失 | 「76年の歴史で初」の休止（詳細日数未確認）、以降発電機・電気系統を地上高所へ移設 | [Community Impact](https://communityimpact.com/houston/bay-area/health-care/2024/07/12/houston-hospitals-navigate-ongoing-outages-as-patient-demand-increases/) |
| 2021/7月 ドイツ西部豪雨 | エシュバイラー市内病院（Eschweiler） | 病院 | 地下浸水、建物設備全損、電力喪失 | 患者約300人をヘリで避難。損害額は建物約5,000万ユーロ＋操業停止損失別途数百万ユーロ | [nhess.copernicus.org](https://nhess.copernicus.org/preprints/nhess-2021-394/nhess-2021-394.pdf) |
| 2021/7月 ドイツ西部豪雨（広域） | ノルトライン＝ヴェストファーレン州内の複数病院・高齢者施設 | 病院・介護施設 | 停電・非常用発電機故障、集中治療室の人工呼吸器患者に危険 | 一部・全部患者避難（施設単位の詳細日数は未確認） | [nhess.copernicus.org](https://nhess.copernicus.org/articles/25/581/2025/) |

---

## 2. ガイドライン・基準の要点と引用可能な数値

### 国交省・経産省「建築物における電気設備の浸水対策ガイドライン」（令和2年6月）
- 出典：[本編PDF](https://www.mlit.go.jp/jutakukentiku/build/content/001349327.pdf)
- 2019年台風19号による武蔵小杉タワーマンション浸水被害を直接の契機に、2019年11月「建築物における電気設備の浸水対策のあり方に関する検討会」設置→2020年6月ガイドライン公表（国交省住宅局建築指導課／経産省産業保安グループ電力安全課）。
- 要点：受変電設備・自家発電設備・付随設備は「想定浸水深」を踏まえ、浸水リスクの少ない場所（地上階・高層階等）に配置することが望ましい。想定浸水深より十分高い位置への設置は、対応行動に左右されない「確実性の高い」対策と位置づけ。
- **要検証**：ガイドライン内の具体的数値基準（浸水深の設定方法、対象規模の閾値等）は検索結果からは断片的にしか確認できておらず、原本PDF（約100頁規模と推定）の精読が必要。

### 「地下空間における浸水対策ガイドライン」（国交省水管理・国土保全局）／「地下街等における浸水防止用設備整備のガイドライン」（平成28年8月）
- 出典：[本編](https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/chika/pdf/honpen.pdf), [平成28年8月版PDF](https://www.mlit.go.jp/common/001142793.pdf)
- 地下街・地下鉄駅・地下駐車場・百貨店地階等、不特定多数が利用する地下空間を対象に浸水防止用設備の設計・管理指針を提供。2016年8月に「浸水防止用設備整備のガイドライン」公表、2017年8月に被害軽減事例集刊行。

### 東京都「豪雨対策基本方針」改定（令和5年＝2023年12月）
- 出典：[報道発表](https://www.spt.metro.tokyo.lg.jp/tosei/hodohappyo/press/2023/12/18/04.html), [中間とりまとめ概要](https://www.toshiseibi.metro.tokyo.lg.jp/documents/d/toshiseibi/pdf_bunyabetsu_bosai_pdf_gouu_pub01)
- 気候変動影響（降雨量1.1倍想定）を踏まえ、目標降雨を都内全域で+10mm引き上げ。
- **数値**：区部では時間75mm降雨に対し浸水被害の防止を目指す（従来目標）。気候変動対応後の新目標降雨は時間85mm（河川整備・下水道整備・流域対策の組み合わせで対応）。
- 5つの施策（河川、下水道、流域対策等）を組み合わせて目標超過降雨にも備える方針。

### 東京都「地下空間浸水対策ガイドライン」改定（令和7年＝2025年9月、直近）
- 出典：[都政総合HP報道発表](https://www.metro.tokyo.lg.jp/information/press/2025/09/2025090903), [概要版PDF](https://www.toshiseibi.metro.tokyo.lg.jp/documents/d/toshiseibi/r7chikashinsuitaisaku-guidelines-gaiyou-2-1)
- 平成20年（2008年）9月策定の旧ガイドラインから17年ぶりの改定。ICT・AI等を活用した防災力強化を含む内容に刷新。地下室・地下駐車場を持つ中小ビル所有者・個人住宅所有者から大規模地下街管理者まで対象。

### 内閣府「事業継続ガイドライン」（令和5年3月版が最新確認、旧第三版から複数回改定）
- 出典：[令和5年3月版PDF](https://www.bousai.go.jp/kyoiku/kigyou/pdf/guideline202303.pdf)
- 2021年4月改定では令和元年台風19号等の水害・土砂災害の教訓を反映し、災害時の外出抑制策等の記述を強化。BCP策定の必要性・手法・リスク分析評価手法を提示（地震のみでなく事業中断要因全般を対象）。

### 宅建業法施行規則改正：水害リスク重要事項説明の義務化（2020年8月28日施行）
- 出典：[国交省Q&A](https://www.mlit.go.jp/totikensangyo/const/content/001354700.pdf), [国交省報道発表](https://www.mlit.go.jp/report/press/totikensangyo16_hh_000205.html)
- 水防法に基づく市町村作成の水害（洪水・雨水出水・高潮）ハザードマップにおける対象物件の所在地説明を宅建業者に義務化。違反・改善命令不履行時は業務停止処分の対象。
- 留意点：物件がハザードマップの浸水想定区域外であっても「水害リスクがない」と誤認させないよう配慮が必要と明記（全日本不動産協会等の解説）。ハザードマップの想定最大規模降雨は年超過確率0.1%（大・中河川のみ対象、小河川は義務対象外）という限界も指摘されている。

### 浸水被害防止区域（特定都市河川浸水被害対策法、2021年改正）
- 出典：[国交省ポータル](https://www.mlit.go.jp/river/kasen/tokuteitoshikasen/portal.html), [概要PDF](https://www.mlit.go.jp/policy/shingikai/content/001442949.pdf)
- 都道府県知事が指定。指定区域内では住宅・要配慮者利用施設の建築時に「居室床面が想定浸水深の水位より高いか」等を事前許可制で確認。非自己居住用住宅・要配慮者利用施設の開発行為も同様に規制対象。

### 治水経済調査マニュアル（案）（国交省水管理・国土保全局、直近改定 令和6年＝2024年4月）
- 出典：[令和6年4月版PDF](https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/r604/chisui_manual.pdf)
- 家屋被害額＝床面積×資産評価額（㎡単価）×浸水深・勾配別被害率、で算定。浸水深別・勾配別の被害率テーブルが存在（家屋・自動車等別）。

### 「水害の被害指標分析の手引」（H25試行版、国交省水管理・国土保全局、2013年7月）
- 出典：[PDF](https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/pdf/higaisihyou_h25.pdf)
- 過去の被災調査に基づき屋根・柱・床等の部材別損害から浸水深別被害率を算出。事業所被害は「損失額＝従業員数×付加価値額×（浸水深別営業停止日数＋営業停止半減日数÷2）」の計算式が存在（検索結果要約、原本での確認推奨）。

### JIS A 4716（浸水防止用設備 建具型）（2019年11月制定）
- 出典：[日本シャッター・ドア協会資料](https://www.jsd-a.or.jp/wp2/wp-content/uploads/2022/03/%E6%B5%B8%E6%B0%B4%E9%98%B2%E6%AD%A2%E7%94%A8%E8%A8%AD%E5%82%99%E8%B3%87%E6%96%99%E5%85%AC%E9%96%8B%E7%94%A8_20220317.pdf)
- 止水板・防水扉等の建具型浸水防止設備について、規定浸水高さにおける漏水量等で性能等級を規定する国内公的規格。

### 会計検査院報告：災害拠点病院の自家発電機浸水対策不備（令和元年度・令和2年度決算検査報告）
- 出典：[令和元年度報告](https://report.jbaudit.go.jp/org/r01/2019-r01-0423-0.htm), [令和2年度報告](https://report.jbaudit.go.jp/org/r02/2020-r02-0401-0.htm)
- 労働者健康安全機構所管13災害拠点病院を検査、複数病院で自家発電機・UPS等の浸水対策未実施を指摘。令和2年度報告では国立病院機構141病院中37災害拠点病院のうち2病院で浸水対策が全く未実施と判明、防水扉・止水板設置や移設等の改善計画策定を要求。

---

## 3. 競合比較表

| サービス | 提供元 | 評価単位 | 入力データ | 地下設備考慮 | 価格帯 | 差別化余地（本アプリにとって） |
|---|---|---|---|---|---|---|
| RisKma（水災害リスクマッピングシステム） | 建設技術研究所 | メッシュ・地点（自治体・企業向けリアルタイム予測） | 気象データ、河川水位、IoT冠水センサー連携 | 明記なし（インフラ管理向け中心、個別建物の地下設備は非対象と推測） | 初期200万〜1,000万円、月額10万〜30万円（検索結果に基づく目安、**要検証**） | 高額・自治体/大企業向け。中小ビルオーナー・個人向けの安価な建物単位一次スクリーニングは手薄 |
| 浸水ナビ（国交省・国総研） | 国土交通省 | 地点（ピンポイント浸水シミュレーション） | 河川氾濫解析データ | 非考慮（建物属性なし） | 無料 | 建物の地下設備・BCP影響は評価対象外。本アプリが接続元データとして活用可能 |
| 不動産情報ライブラリ | 国土交通省 | 地図・メッシュ・地点（防災情報API配信開始済み） | 洪水浸水想定区域、土砂災害警戒区域等の行政データ | 非考慮 | 無料（API含む） | 一次データソースとして活用可、建物単位の「機能停止リスク」への変換は本アプリの付加価値領域 |
| 東京海上ディーアール 自然災害リスク評価（水災） | 東京海上グループ | 拠点・建物単位（企業の事業拠点） | ハザードマップ＋現地調査＋洪水氾濫シミュレーション | 考慮あり（設備被害想定、事業継続性評価まで実施） | BtoB個別見積り（非公開、高額と推測） | 高精度だがコンサル型で個別受託・高コスト。オープンデータでのセルフ一次スクリーニング（安価・迅速）に差別化余地 |
| 三井住友海上・損保ジャパン等の水災リスク評価 | 各損保 | 詳細不明（検索では確認不可） | 不明 | 不明 | 不明 | **要検証**：各社サイトの直接調査が必要 |
| First Street Foundation / Flood Factor | 米国First Street | 物件（建物フットプリント）単位 | 高解像度洪水モデル（河川・高潮・内水氾濫）、気候変動シナリオ反映 | 建物の物理的属性（地下等）を明示的に評価するかは不明（浸水到達確率・深さ中心） | 個人向け無料（Webサイト）、法人向けAPIは有料 | 米国限定。日本市場には直接競合しないが、スコアリング設計（1-10スコア、30年確率）の参考モデルとして有用 |
| JBA Risk Management（Global Flood Model） | JBA UK | メッシュ・建物フットプリント（disaggregation改良） | 独自水文モデル、建物フットプリントデータ、気候シナリオ | 建物単位の位置精度は向上しているが、地下設備等の建物内部属性は非考慮と推測 | BtoB（保険・再保険向け、非公開） | 保険引受向け、一般消費者・中小事業者には非提供 |
| Fathom | 英Fathom | メッシュ・グローバル高解像度 | 独自洪水モデル | 非考慮（ハザード層のみ） | BtoB非公開 | 同上 |
| Munich Re Location Risk Intelligence | Munich Re | 地点（住所単位、15種以上のハザードスコア） | 複数ハザードデータ統合、ICEYE衛星浸水データ連携（リアルタイム） | 非考慮（ハザードスコア中心、建物内部設備は対象外と推測） | SaaS、BtoB契約（非公開） | 建物内部の脆弱性（設備配置等）までは踏み込んでいない可能性が高く、本アプリの主要差別化ポイント |
| LIFULL HOME'S ハザードマップ機能 | LIFULL | 地点（物件検索連動） | 国交省ハザードマップをオーバーレイ表示 | 非考慮 | 無料（不動産検索の付随機能） | 単純表示のみで一次スクリーニング・対策提案機能なし。本アプリが機能面で上位互換となりうる |
| 東京カンテイ | 東京カンテイ | 不明（検索で詳細確認できず） | 不明 | 不明 | 不明 | **要検証** |
| ゼンリン建物ポイントデータ等 | ゼンリン | 建物単位（位置座標のみ、全国約3,900万棟） | 住宅地図ベースの建物ポイント | 非考慮（属性データではなく位置データ中心） | BtoB（データ販売、非公開） | 建物位置の基盤データとして本アプリのベースマップに活用可能。リスク評価機能自体は非提供 |
| パスコ MarketPlanner等 | パスコ | メッシュ・エリア（マーケティング用途中心） | 人口統計・地理データ | 非考慮 | BtoB非公開 | 直接競合ではない |

**総括（推測を含む）**：国内外とも「ハザード（外力）評価」または「企業向け個別コンサル」の二極化が進んでおり、①建物単位、②オープンデータのみで完結、③地下設備配置を機能停止リスクとして定量化、④対策提案まで自動生成、の4条件を同時に満たす安価なセルフサービス型ツールは検索範囲では確認できなかった。ここが本アプリの潜在的なホワイトスペースと考えられる（**要検証**：日本語での類似スタートアップ・研究プロトタイプの追加調査推奨）。

---

## 4. 学術・技術的知見

- **治水経済調査マニュアル／水害の被害指標分析の手引**（国交省水管理・国土保全局）：浸水深別・勾配別の家屋被害率、事業所営業停止日数（＋営業停止半減日数）を用いた損失額算定式が公的に整備されている。スコアリングの重み付け根拠として直接引用可能。[令和6年4月版マニュアル](https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/r604/chisui_manual.pdf)、[H25被害指標分析の手引](https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/pdf/higaisihyou_h25.pdf)
- **地下空間浸水過程の研究**：河田恵昭・後藤隆一「市街地氾濫時の地下空間浸水過程と被害軽減」（土木学会海岸工学論文集第47巻、2000年）など、地下空間への流入速度・階段部の歩行困難水位等の実験研究が存在。[J-STAGE](https://www.jstage.jst.go.jp/article/proce1989/47/0/47_0_1246/_pdf/-char/ja)
- **土木学会 地下空間研究委員会／論文集F2（地下空間研究）**：地下空間利用・地下防災・地下浸水を扱う専門分野が確立。[委員会サイト](https://www.jsce-ousr.org/)
- **国総研 危機管理技術研究センター水害研究室**：大都市地下空間と地上部の浸水を同時解析する技術開発（氾濫水の地下流入・貯留・移動のシミュレーション）。[論文PDF](https://www.nilim.go.jp/lab/rcg/newhp/seika.files/pdf/ronbun_3.pdf)
- **医療機関の水害初動対応研究**：湯浅恭史・中野晋・岡野将希「豪雨被災事例からみる医療機関における浸水被害時の初動対応と事業継続についての考察」（土木学会論文集特集号、確認済みPDFあり）。[J-STAGE PDF](https://www.jstage.jst.go.jp/article/jscejsp/75/2/75_I_217/_pdf/-char/ja)
- **住宅の洪水時耐浸水性能研究**：日本建築防災協会・建築研究所共同研究（令和5年度建築基準整備促進事業）。[国交省PDF](https://www.mlit.go.jp/jutakukentiku/build/content/001742051.pdf)
- **機械学習による地下階推定の先行研究**：検索範囲では日本国内の学術研究として明確な該当論文は確認できず（**未確認・要検証**）。米欧では建物フットプリント×衛星/LiDARを用いた建物属性推定（階数・用途等）の研究は存在する可能性が高いが、地下階に特化した推定モデルの一次資料は本調査では特定できなかった。

---

## 5. 対策メニューの根拠

| 対策 | 効果・仕様の根拠 | 出典 |
|---|---|---|
| 止水板・防水扉（固定式／脱着式／自動式） | 費用目安：固定式10-20万円、脱着式20-30万円、自動式30-50万円。多くの自治体で費用の1/2〜2/3（上限10-50万円程度）の助成金あり。浸水深が出入口側壁高さを超える場合は単独では防御不能（側壁・屋根含む改修が必要） | [ALSOK](https://www.alsok.co.jp/person/recommend/2178/), [防災ベーシック](https://bousai-base.com/flood-barrier-guide/) |
| JIS A 4716認証品の止水設備 | 規定浸水高さでの漏水量に基づく性能等級を国が規定（2019年11月制定） | [JSD-A資料](https://www.jsd-a.or.jp/wp2/wp-content/uploads/2022/03/%E6%B5%B8%E6%B0%B4%E9%98%B2%E6%AD%A2%E7%94%A8%E8%A8%AD%E5%82%99%E8%B3%87%E6%96%99%E5%85%AC%E9%96%8B%E7%94%A8_20220317.pdf) |
| 設備かさ上げ・高所移設（受変電設備・自家発電機） | 国交省ガイドライン推奨。想定浸水深より十分高い位置への設置は「対応行動によらず確実性の高い」対策と明記。ヒューストンのMemorial Hermann病院、Texas Children's Hospitalは実際に発電機・電気系統を地上/高層階へ移設した実例あり | [国交省ガイドライン](https://www.mlit.go.jp/jutakukentiku/build/content/001349327.pdf), [Community Impact記事](https://communityimpact.com/houston/bay-area/health-care/2024/07/12/houston-hospitals-navigate-ongoing-outages-as-patient-demand-increases/) |
| 可搬式止水（プラバリア＝積水テクノ成型） | 2m止水につき、土嚢は2人×40分必要に対し、プラバリアは1人×2分で設置可能。重量は土嚢1個20kg対しプラバリア1個4kg。角度30度刻みで調整可、積み重ね収納可 | [積水化学プレスリリース](https://www.sekisui.co.jp/news/2024/1404535_41090.html), [テライド製品情報](https://www.teraido.jp/cm/prod/PlaBarrier) |
| 浸水検知センサー（IoT冠水センサー） | RisKmaが高性能カメラ・冠水センサー等IoTデバイスと連携する事例あり（Braveridge社との協業） | [Braveridge事例](https://www.braveridge.com/case_study/CTI_RisKma) |
| グリーンインフラ（雨庭・バイオスウェル・貯留槽） | 東急建設が2023年度国交省「グリーンインフラ創出促進事業」採択事業として大型商業施設内で実証、複数の雨庭（貯留容量約5.5〜63㎥/基）とバイオスウェルにより「集水経路での浸透」「窪地での浸透」「窪地での貯留」の3機能で雨水流出抑制効果を確認・運用開始後も効果を検証済み | [東急建設プレスリリース](https://www.tokyu-cnst.co.jp/topics/2662.html), [ITmedia記事](https://built.itmedia.co.jp/bt/articles/2409/09/news141.html) |
| 雨庭による敷地内雨水流出抑制（学術検証） | 清水建設・東京都市大学の共同研究発表あり | [PDF](https://www.uit.gr.jp/gijutu/file/02/c01_r01.pdf) |
| 防水扉・止水板の病院設置改善計画 | 会計検査院が浸水対策未実施の災害拠点病院に対し、自家発電機の移設または防水扉・止水板設置の計画策定を「改善の処置」として要求（公式に効果が認知された対策としての位置づけ） | [会計検査院R1報告](https://report.jbaudit.go.jp/org/r01/2019-r01-0423-0.htm) |

---

## 6. 法的・倫理的留意点

- **重要事項説明義務との関係**：宅建業法上、水害ハザードマップの説明義務は既に存在するが、対象は「水防法ベースの公式ハザードマップ」のみ。本アプリの独自スコアは法定書類ではないため、宅建業者の説明義務を代替するものではない旨を明記する必要（**要専門家確認**：不動産取引実務・宅建業法の解釈は弁護士等への確認推奨）。
- **免責表記の実務**：ハザードマップの想定最大規模降雨は年超過確率0.1%であり、かつ大・中河川のみが法的義務対象（小河川は対象外）という限界が既に業界内で認識されている。本アプリのスコアも「特定の外力・特定条件下でのシミュレーション結果であり、実際の被害を保証するものではない」旨の明確な免責が必要。
- **不動産価値・風評被害リスク**：検索結果では「ハザードマップ公開が地価に与える影響は限定的」との見方が優勢（鑑定評価に既に災害リスクが織り込まれているため）だが、個別取引では買主による値引き交渉やクレームの引き金になる実例が指摘されている。**本アプリが独自算出する「機能停止リスクスコア」を建物単位・実名で公開する場合、既存の公的ハザードマップ以上の風評影響を及ぼす可能性があり、公開範囲（所有者限定／匿名化／自治体単位集約等）の設計判断が必要**（推測を含む論点、要事業判断）。
- **地下設備位置情報のセキュリティ**：受変電設備・発電機の設置階・位置情報はテロ・犯罪対策上機微な情報となりうる。BCP関連の物理セキュリティ情報を一般公開APIに含める場合は、アクセス制御（所有者・管理者限定等）を検討する必要（本調査で直接の事例は確認できず、**推測に基づく論点**）。
- **公的データの二次利用条件**：不動産情報ライブラリ、国土数値情報、浸水ナビ等のAPI・データの利用規約（商用利用可否、クレジット表記義務等）は個別に確認が必要（**要検証**）。

---

## 7. 未確認事項・要検証リスト

1. 「建築物における電気設備の浸水対策ガイドライン」原本PDF内の具体的数値基準（想定浸水深の設定方法の詳細、0.5m/3m等の閾値の有無）→ 原本精読が必要。
2. 三井住友海上、損保ジャパン、あいおいニッセイ同和損保の水災リスク評価サービスの詳細（評価単位、価格、地下設備考慮の有無）→ 各社サイト・ IR資料の追加調査が必要。
3. 東京カンテイの水害リスク関連サービスの有無・詳細→追加調査が必要。
4. RisKmaの価格情報（初期200万〜1,000万円、月額10万〜30万円）は検索結果の要約情報であり、一次資料（見積り・料金表）での確認が取れていない。
5. 日本国内における「機械学習による建物地下階推定」の学術研究の有無→本調査では特定できず、追加のJ-STAGE・CiNii検索が必要。
6. 名古屋市営地下鉄浸水事例（2000年、検索結果内言及）の日付・詳細→一次資料未確認。
7. 東急建設の「浸水検知センサー」単体製品としての具体的プレスリリース→今回の検索では雨水流出抑制（グリーンインフラ）関連情報のみ確認でき、単体の「浸水検知センサー」製品情報は特定できず（RisKma側のIoT冠水センサー連携事例は確認）。
8. 各データ・API（不動産情報ライブラリ、国土数値情報等）の商用利用規約詳細。
9. 本アプリのスコア公開が宅建業法上の重要事項説明義務とどう関係するか（代替可能か、あくまで補助情報か）の法的整理→弁護士等専門家への確認を推奨。
10. 会計検査院報告以降（令和3年度以降）の災害拠点病院の対策進捗状況の最新データ。

---

## 8. 参照URL一覧

### 被災事例
- https://xtech.nikkei.com/atcl/nxt/column/18/00154/00858/
- https://xtech.nikkei.com/atcl/nxt/column/18/01027/102200019/
- https://xtech.nikkei.com/atcl/nxt/mag/na/18/00111/080500003/
- https://business.nikkei.com/atcl/gen/19/00002/101800785/
- https://www.tokyo-np.co.jp/article/60914
- https://business.nikkei.com/atcl/gen/19/00178/071400002/
- https://bijutsutecho.com/magazine/news/headline/21286
- https://bijutsutecho.com/magazine/news/headline/23331
- https://www.nikkei.com/article/DGXMZO53008260V01C19A2L82000/
- https://www.city.kawasaki.jp/250/page/0000122172.html
- https://www.city.kawasaki.jp/601/cmsfiles/contents/0000111/111602/03myuujiamukenshou.pdf
- https://www.tokyo-np.co.jp/article/91762
- https://article.yahoo.co.jp/detail/23da87f46400431cde8f1047ac467f860d35393b
- https://www.tokyo-np.co.jp/article/440444
- https://meguro.goguynet.jp/2025/10/02/fullelwith_jiyugaoka5/
- https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20251010fullel.pdf
- https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20250916fullel.pdf
- https://www.tokyu-store.co.jp/Portals/0/PDF/oshirase/oshirase2025/20251202fullel.pdf
- https://xtech.nikkei.com/atcl/nxt/column/18/00154/02908/
- https://www.m3.com/news/open/iryoishin/1353493
- https://news.yahoo.co.jp/articles/e45724e3d399d229d8740ad13a0f60e07492f538
- https://www.kensetsu-plaza.com/kiji/post/22019
- https://ja.wikipedia.org/wiki/%E9%BA%BB%E5%B8%83%E5%8D%81%E7%95%AA%E9%A7%85
- https://www.datacenterknowledge.com/business/massive-flooding-damages-several-nyc-data-centers
- https://www.foxnews.com/us/efforts-to-defend-nyc-hospitals-against-flood-break-down-in-sandys-torrent
- https://communityimpact.com/houston/bay-area/health-care/2024/07/12/houston-hospitals-navigate-ongoing-outages-as-patient-demand-increases/
- https://www.cbsnews.com/amp/news/flooding-disrupts-care-at-houston-hospital-cancer-center
- https://nhess.copernicus.org/preprints/nhess-2021-394/nhess-2021-394.pdf
- https://nhess.copernicus.org/articles/25/581/2025/

### ガイドライン・法規制
- https://www.mlit.go.jp/jutakukentiku/build/content/001349327.pdf
- https://www.mlit.go.jp/jutakukentiku/build/content/001348131.pdf
- https://sustainablejapan.jp/2020/06/23/flood-electrical-equipment/51176
- https://www.mlit.go.jp/common/001142793.pdf
- https://www.mlit.go.jp/river/basic_info/jigyo_keikaku/saigai/tisiki/chika/pdf/honpen.pdf
- https://www.mlit.go.jp/toshi/content/001365723.pdf
- https://www.spt.metro.tokyo.lg.jp/tosei/hodohappyo/press/2023/12/18/04.html
- https://www.toshiseibi.metro.tokyo.lg.jp/documents/d/toshiseibi/pdf_bunyabetsu_bosai_pdf_gouu_pub01
- https://www.toshiseibi.metro.tokyo.lg.jp/bosai/chisui/chisui/gouu_houshin
- https://www.metro.tokyo.lg.jp/information/press/2025/09/2025090903
- https://www.toshiseibi.metro.tokyo.lg.jp/documents/d/toshiseibi/r7chikashinsuitaisaku-guidelines-gaiyou-2-1
- https://www.bousai.go.jp/kyoiku/kigyou/pdf/guideline202303.pdf
- https://www.mlit.go.jp/totikensangyo/const/content/001354700.pdf
- https://www.mlit.go.jp/report/press/totikensangyo16_hh_000205.html
- https://www.mlit.go.jp/river/kasen/tokuteitoshikasen/portal.html
- https://www.mlit.go.jp/policy/shingikai/content/001442949.pdf
- https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/r604/chisui_manual.pdf
- https://www.mlit.go.jp/river/basic_info/seisaku_hyouka/gaiyou/hyouka/pdf/higaisihyou_h25.pdf
- https://www.jsd-a.or.jp/wp2/wp-content/uploads/2022/03/%E6%B5%B8%E6%B0%B4%E9%98%B2%E6%AD%A2%E7%94%A8%E8%A8%AD%E5%82%99%E8%B3%87%E6%96%99%E5%85%AC%E9%96%8B%E7%94%A8_20220317.pdf
- https://report.jbaudit.go.jp/org/r01/2019-r01-0423-0.htm
- https://report.jbaudit.go.jp/org/r02/2020-r02-0401-0.htm

### 競合サービス
- https://www.riskma.net/ja/top
- https://www.ctie.co.jp/news/uploads/2021/03/riskma-leaflet.pdf
- https://digital-service-catalog.digital.go.jp/service/a0PQ800000Qq9AbMAJ/a000562
- https://www.reinfolib.mlit.go.jp/map/
- https://suiboumap.gsi.go.jp/
- https://www.mlit.go.jp/report/press/tochi_fudousan_kensetsugyo17_hh_000001_00068.html
- https://www.tokio-dr.jp/service/natural_risk_assessment/water/
- https://www.tokio-dr.jp/service/natural_risk_reduction/flood_damage/
- https://help.firststreet.org/hc/en-us/articles/1500000359741-Flood-Model-Methodology-Calculating-property-level-risk
- https://help.firststreet.org/hc/en-us/articles/360047585694-How-is-my-Flood-Factor-calculated
- https://www.jbarisk.com/flood-services/catastrophe-models/flood-models/
- https://www.fathom.global/wp-content/uploads/2021/12/Flood-Emergency-Report-Germany-2021-1_compressed.pdf
- https://www.munichre.com/rmp/en/products/location-risk-intelligence.html
- https://www.munichre.com/rmp/en/the-re-brief/risk-management/from-forecast-to-footprint.html
- https://ascii.jp/elem/000/004/059/4059366/
- https://lifull.com/news/18173/
- https://www.zenrin.co.jp/product/category/gis/contents/building-point/index.html

### 学術・技術知見
- https://www.jstage.jst.go.jp/article/proce1989/47/0/47_0_1246/_pdf/-char/ja
- https://www.jsce-ousr.org/
- https://www.nilim.go.jp/lab/rcg/newhp/seika.files/pdf/ronbun_3.pdf
- https://www.jstage.jst.go.jp/article/jscejsp/75/2/75_I_217/_pdf/-char/ja
- https://www.mlit.go.jp/jutakukentiku/build/content/001742051.pdf

### 対策メニュー
- https://www.alsok.co.jp/person/recommend/2178/
- https://bousai-base.com/flood-barrier-guide/
- https://www.sekisui.co.jp/news/2024/1404535_41090.html
- https://www.teraido.jp/cm/prod/PlaBarrier
- https://www.braveridge.com/case_study/CTI_RisKma
- https://www.tokyu-cnst.co.jp/topics/2662.html
- https://built.itmedia.co.jp/bt/articles/2409/09/news141.html
- https://www.uit.gr.jp/gijutu/file/02/c01_r01.pdf

### 法的・倫理的留意点
- https://kaitori.openhouse-group.com/column/knowledge/037/
- https://sakk.jp/adex/appraisal/%E3%83%8F%E3%82%B6%E3%83%BC%E3%83%89%E3%83%9E%E3%83%83%E3%83%97%E3%81%8C%E4%B8%8D%E5%8B%95%E7%94%A3%E4%BE%A1%E6%A0%BC%E3%81%AB%E4%B8%8E%E3%81%88%E3%82%8B%E5%BD%B1%E9%9F%BF%E2%94%80%E2%94%80%E4%B8%8D/
- https://www.zennichi.or.jp/law_faq/%E6%B0%B4%E5%AE%B3%E3%83%8F%E3%82%B6%E3%83%BC%E3%83%89%E3%83%9E%E3%83%83%E3%83%97%E4%B8%8A%E3%81%AE%E5%AF%BE%E8%B1%A1%E7%89%A9%E4%BB%B6%E3%81%AE%E4%BD%8D%E7%BD%AE%E3%81%AE%E8%AA%AC%E6%98%8E/
- https://www.homes.co.jp/cont/press/buy/buy_01887/
