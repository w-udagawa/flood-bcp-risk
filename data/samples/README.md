# サンプルデータ（架空）

このディレクトリの `features_sample.csv` と `answers_sample.csv` は、
floodbcp（スコアリングエンジン）のテスト・デモ用に作成した**完全に架空**の
建物・診断回答データです。実在の建物・施設・住所・法人とは一切関係ありません。
`building_id` は `bldg_sample_NNN` という連番のダミー ID、`name` は「架空:」
接頭辞を付けた仮名です。ward_code は目黒区(13110)・世田谷区(13112)・大田区(13113)
の実在コードを地域感を出すために借用していますが、建物そのものは実在しません。

## features_sample.csv

列は `config/features_schema.json`（`docs/03_スコアリング仕様.md` 第1章）に
準拠します。欠損は空文字です。20 件収録し、以下の多様性を持たせています。

- 用途：hospital, station（乗降客数多/少）, datacenter, public_critical,
  commercial_large, commercial, office, welfare, logistics（延床大/小）,
  school, residential_large, residential（対象外）, other（延床 3,000 未満/以上）
- 欠損パターン：内水・洪水・高潮のすべてが null（`insufficient_data` になるもの、
  浸水実績があり H=2 暫定で継続するもの）、storeys_below 不明（用途から推定）、
  内水・洪水は null で高潮（surge）のみデータあり（`bldg_sample_020`。内水・洪水・
  高潮のいずれか1つでもデータがあれば H は算出できるため `assessed` となり、
  H は surge の下限値から算出される）
- シナリオ：
  - `bldg_sample_001`：自由が丘型（commercial_large、storeys_below=1、
    内水 0.5–1.0 m、延床 ≥10,000、浸水実績あり）→ 優先度 A を想定
  - `bldg_sample_002`：病院・地下なし・ハザードなし（区域外データあり）
    → 優先度 D または C（本サンプルでは I=4 のため C）を想定

## answers_sample.csv

`docs/03_スコアリング仕様.md` 第6章の Tier1 簡易診断（Q1〜Q12）の回答例です。
値は `yes` / `no` / `unknown`（空欄も `unknown` として扱われます）。
全建物ではなく一部の `building_id` のみ収録しており、Tier1 上書きルール
（Q3 決定的、止水設備3条件での -2 等）を CLI エンドツーエンドで確認する
ためのものです。
