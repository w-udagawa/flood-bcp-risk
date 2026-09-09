# web/ 静的ビューア試作（TASK-005）

浸水時事業停止リスク診断（flood-bcp-risk）の評価結果（assessment）を、地図と建物カルテで
閲覧するための静的 Web の試作。ビルド不要。単一の `index.html` + `app.js` + サンプル
GeoJSON/JSON で構成する。

## 起動方法

npm は使わない。ビルドも不要。Python 3 標準の HTTP サーバで `web/` を配信する。

```sh
cd web
python3 -m http.server 8000
```

ブラウザで `http://localhost:8000/` を開く（`fetch` で `data/*.json` を読むため、
`file://` で直接開くとブラウザによっては CORS エラーになる。必ず HTTP サーバ経由で開くこと）。

## 構成

| ファイル | 内容 |
|---|---|
| `index.html` | 地図・フィルタ・検索・凡例・カルテ用サイドパネルの DOM とスタイル、出典・免責表示 |
| `app.js` | データ読込、地図初期化・レイヤ切替、フィルタ/検索の適用、建物カルテ描画（DOM 操作） |
| `lib/join.js` | `buildings.geojson` と `assessments.json` を `building_id` で結合する純関数、色・ラベル関数。ブラウザ（`window.FloodBcpJoin`）と Node（`node --test`）の両方から使える UMD 風モジュール |
| `data/buildings_sample.geojson` | 架空のサンプル建物ポリゴン 15 件（目黒区自由が丘駅周辺、おおよそ 35.6075N, 139.6690E） |
| `data/assessments_sample.json` | 上記に対応する架空の評価結果 15 件（`docs/03_スコアリング仕様.md` 第11章のスキーマに準拠） |
| `data/measures.json` | 対策候補メニュー M-01〜M-11（`docs/03_スコアリング仕様.md` 第13章の複製。正本は将来 `config/measures.json`） |
| `tests/join.test.js` | `lib/join.js` のユニットテスト（`node --test`） |

## CDN 依存

MapLibre GL JS を CDN から `<script>`/`<link>` で読み込む（npm install はしない）。

- `https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js`
- `https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css`

バージョンは `4.7.1` に固定。**本環境は外部ネットワークへのアクセスが組織ポリシーで
ブロックされており（`cdn.jsdelivr.net` への CONNECT が 403）、このバージョンが実在し
配信されることを本タスクの中では確認できていない。** ブラウザで開く前に、実際に
`https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js` が 200 を返すか、
またはより新しい 4.x 系の固定バージョンに更新する必要がないかを確認すること。

ベースマップは地理院タイル（淡色地図、`https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png`）
を出典表示付きで使用する。

## テスト・構文チェック

```sh
# Node 22 標準の node:test / node:assert のみ使用（外部パッケージ不可）
node --test web/tests/join.test.js
# または web/ ディレクトリ内で（自動探索）
cd web && node --test

# 構文チェック
node --check web/app.js
node --check web/lib/join.js
```

**既知の環境上の癖**：この実行環境の Node 22.22.2 では、`node --test web/tests/`
のようにディレクトリを直接指定すると `Cannot find module` で失敗する（`/tmp` 上の
無関係な最小再現でも同じ症状が出るため、本プロジェクト固有の問題ではなく実行環境側の
挙動と考えられる）。ファイルを明示するか（`node --test web/tests/join.test.js`）、
glob を渡すか（`node --test 'web/tests/*.test.js'`）、`web/` に `cd` して引数なしで
実行する（`node --test`、カレントディレクトリを自動探索）と正常に動く。他の環境では
`node --test web/tests/` がそのまま通る可能性がある。

## PMTiles への置き換え方針（フェーズ M3）

現状は GeoJSON をそのまま `fetch` して MapLibre の `geojson` ソースに渡している
（15 件程度の試作データ向け）。建物数が区単位（10 万棟規模、NFR-03）に増えた場合は
クライアント側 GeoJSON では性能・転送量の面で破綻するため、以下へ移行する。

1. ETL（`pipelines/`）の出力（建物ポリゴン＋評価結果を結合した GeoJSON/FlatGeobuf）を
   `tippecanoe` で ベクトルタイル化し、`PMTiles` 形式で 1 ファイルに固める
   （`docs/02_要件定義書.md` 第10章のアーキテクチャ図のとおり）。
2. `web/` 側は `pmtiles` ライブラリ（CDN 読み込み、npm 不要）を使い、MapLibre の
   `protocol` として登録した上で `source.type = "vector"` + `url: "pmtiles://…"` に切り替える。
3. 色分け・フィルタのロジックは `lib/join.js` の関数をできる限り流用する。ただし
   ベクトルタイル化後は結合済みデータを配信するため、クライアント側での
   `joinBuildingsWithAssessments` 呼び出しは不要になり、代わりにタイル内プロパティを
   直接参照する形に置き換える（色・ラベル関数は流用可能）。
4. 検索・フィルタは全件を保持できなくなるため、別途一覧 API（非公開層 `api/`）または
   タイル外の軽量インデックス（building_id・名称・優先度のみの小さな JSON/SQLite）を
   別途用意する方針を検討する。
5. 静的ホスティング（S3 等）から PMTiles を HTTP Range リクエストで読む構成に変更する
   （追加サーバ不要、CDN のみで完結）。

## docs との差異・簡略化（仕様との差異）

TASK-005 は試作であり、以下は仕様書の全機能ではなく縮小・簡略化している。

- **フィルタ**：`docs/02_要件定義書.md` FR-05 は「用途、優先度、地下階の有無、浸水深、
  確信度、管理施設のみ、要確認のみ」だが、本試作は TASK-005 の指示どおり
  「用途・優先度・要確認のみ」の3種類のみ実装。地下階・浸水深・確信度レンジ・
  管理施設のフィルタは未実装（フェーズ2以降、非公開層と合わせて拡張想定）。
- **要確認のみの定義**：`docs/03_スコアリング仕様.md` 第9章の確信度ルール
  （`C < 50 かつ P ≥ 2` で優先度を1段階繰り上げ、`*` を付す）に基づき、
  `assessment.priority_raised_by_low_confidence === true` の建物のみを抽出する
  仕様として実装した。要件定義書・スコアリング仕様書に「要確認のみ」フィルタの
  厳密な定義がなかったため、この解釈で実装している。
- **不足情報・優先確認事項・対策候補の生成**：本来はスコアリングエンジン
  （`floodbcp/`、別タスク）が `docs/03_スコアリング仕様.md` 第12・13章の規則に従って
  算出し `assessments.json` に格納する。本試作のサンプルデータはビューア単体で
  動作確認するために `web/` 側で簡略化した生成ロジック（V≥2、I≥3 の条件のみ）で
  作成した架空データであり、Q1〜Q12（簡易診断）や `footprint_area_m2`・
  `depression_flag`・`rel_elev_m` を用いる対策候補（M-02〜M-06、M-08、M-09、M-11 等）
  は反映していない。実データでは `floodbcp/` の出力をそのまま `data/` に配置すればよい。
- **簡易診断（Tier 1、FR-09）へのリンク**：カルテ内に導線の説明文のみ表示し、
  実際の12問フォームは実装していない（非公開層 `api/` が必要なため、フェーズ2）。
- **管理施設一覧・レポート出力（FR-08、FR-11）**：本試作の対象外（TASK-005 の
  出力物に含まれない）。
- **ハザード種別・DEM・実績・地形分類レイヤ（FR-04 の一部）**：本試作は
  優先度・H・V・I・C の色分けのみ実装。内水／洪水／高潮個別レイヤ、DEM 陰影、
  実績レイヤ、地形分類レイヤは未実装（要件定義書 11章の「マップ」要素の一部を
  スコープアウト）。
- **建物データ・評価結果データモデル**：`docs/02_要件定義書.md` 第9章の
  `building` テーブルには `usage_code`（PLATEAU 由来コード）のみが定義されているが、
  本試作の `data/buildings_sample.geojson` にはフィルタ表示用に `usage_class`
  （`docs/03_スコアリング仕様.md` 第2章の分類）も便宜的に追加している。実データ生成時は
  ETL（`pipelines/`）が `usage_code` から `usage_class` を導出して building 側にも
  持たせるか、Web 側で別途変換する必要がある。

## 未検証事項（ブラウザ未確認）

**本環境ではブラウザでの動作確認ができていない。** 品質は以下でのみ担保している。

- `node --check web/app.js web/lib/join.js`（構文的妥当性のみ。実行時エラーは検出できない）
- `node --test web/tests/`（`lib/join.js` のデータ結合・色分け・フィルタ・検索ロジックの
  ユニットテスト。DOM・MapLibre 呼び出しは対象外）
- `python3 -c "html.parser"` によるおおまかな HTML 構文チェックとタグ対応の目視・機械カウント

以下は実ブラウザでの確認が必要（未検証）。

- MapLibre GL JS の CDN 読み込みが実際に成功するか（上記「CDN 依存」参照。ネットワーク
  ポリシーにより本タスク内では検証不可）。
- 地理院タイルへのアクセスが CORS・Referrer ポリシー等でブロックされないか。
- `fill-color` / `line-color` に文字列で渡している 16進カラーコードが MapLibre の
  スタイル式として問題なく解釈されるか（`['get', 'fill_color']` で GeoJSON の
  properties から取得する形にしている）。
- レイアウト（グリッド・サイドパネルのスクロール等）が実際のウィンドウサイズで崩れないか。
- クリック・ホバーのイベントハンドラ（`buildings-fill` レイヤ）が期待どおり発火するか。
- モバイル幅（`@media (max-width: 900px)`）でのレイアウト崩れ。

## サンプルデータについて

`data/` 配下のデータはすべて架空である。目黒区自由が丘駅周辺のおおよその座標
（35.6075N, 139.6690E）を中心に、実在しない矩形ポリゴン15件・施設名・住所を
機械的に生成したものであり、実在の建物・施設・住所とは一切関係ない。
