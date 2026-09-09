"""PLATEAU bldg:usage コード → usage_class（本システムの用途分類）写像。

標準ライブラリのみで完結する純 Python モジュール（GIS 依存なし）。

参照:
  - docs/03_スコアリング仕様.md 第 2 章（usage_class 定義・規模条件）
  - docs/tasks/TASK-003_ETL骨格.md（PLATEAU bldg:usage コード例の指定）
  - docs/research/A_建物データ調査.md（PLATEAU 属性調査。usage コード表自体の
    一次資料未確認である旨の記載あり）

**重要な注意（未検証・要確認）**:
  タスクカード記載のコード表（Building_usage.xml 由来とされる 401/402/... の
  3 桁コードと日本語名の対応）は、本開発環境（WebFetch 不可）では一次資料
  （PLATEAU 定義文書 `bldg_Building.html` 等）を直接確認できていない。
  `docs/research/A_建物データ調査.md` も「用途コードの一次資料は未検証」と
  明記している。したがって下記 ``USAGE_CODE_TABLE`` は **未検証** であり、
  実データ（目黒区 2025 / 世田谷区 2023 の CityGML）を PLATEAU GIS Converter
  等で開いて実際の bldg:usage 値をサンプリングし、要確認・要修正である
  （関連: 要件定義書 16 章 V-01）。

  また、PLATEAU の usage コード単体では hospital（病院）・datacenter・
  station（駅）・welfare（福祉）を確実に判別できない設計とした。
  これらは P04（医療機関）・P14（福祉施設）・N02（鉄道）などの外部データとの
  空間結合結果（hospital_flag 等のヒント引数）で上書きする。
"""

from __future__ import annotations

# usage_code(3桁, str) -> 基礎 usage_class（規模条件反映前）。
# 値は docs/tasks/TASK-003_ETL骨格.md に列挙されたコードのみを対象とする。
# コード自体の意味・網羅性は未検証（上記モジュール docstring 参照）。
USAGE_CODE_TABLE: dict[str, str] = {
    "401": "office",        # 業務施設
    "402": "commercial",    # 商業施設（延床規模で commercial_large に格上げ）
    "403": "commercial",    # 宿泊施設 -- 用途区分が本システムの分類に無いため
                             # commercial 扱いとした。仮の割当て、要確認。
    "404": "commercial",    # 商業系複合施設（延床規模で commercial_large に格上げ）
    "411": "residential",   # 住宅
    "412": "residential",   # 共同住宅（規模条件で residential_large に格上げ）
    "413": "residential",   # 店舗等併用住宅
    "414": "residential",   # 店舗等併用共同住宅（規模条件で residential_large に格上げ）
    "415": "residential",   # 作業所併用住宅
    "421": "public_critical",  # 官公庁施設
    "422": "school",        # 文教厚生施設 -- 学校・病院・福祉施設等を包含し得る
                             # 括りとされ、本表単独では school を仮当てし、
                             # hospital_flag / welfare_flag（P04/P14 結合）が
                             # あればそちらを優先する。要確認。
    "431": "logistics",     # 運輸倉庫施設 -- 駅関連施設もこのコードに含まれ
                             # 得るため、station_hint（N02 鉄道との空間結合）
                             # があれば station を優先する。要確認。
    "441": "other",         # 工場 -- 本システムの usage_class に対応区分が
                             # 無いため other 扱い。要確認。
    "451": "other",         # 農林漁業用施設
    "452": "other",         # 供給処理施設
    "453": "other",         # 防衛施設 -- public_critical（庁舎・防災拠点・
                             # 警察・消防）の定義に軍事施設が含まれるか不明の
                             # ため、保守的に other とした。要確認。
    "454": "other",         # その他
    "461": "other",         # 空地（建物ポリゴンが存在しない想定だが念のため定義）
    "462": "other",         # 不明
}

# usage_class として妥当な値の集合（features_schema.json の説明文と一致させる）
VALID_USAGE_CLASSES = frozenset(
    {
        "hospital",
        "station",
        "datacenter",
        "public_critical",
        "commercial_large",
        "commercial",
        "office",
        "welfare",
        "logistics",
        "school",
        "residential_large",
        "residential",
        "other",
    }
)

# 規模条件の閾値（docs/03_スコアリング仕様.md 第2章）
COMMERCIAL_LARGE_FLOOR_AREA_M2 = 10_000.0
RESIDENTIAL_LARGE_FLOOR_AREA_M2 = 10_000.0
RESIDENTIAL_LARGE_STOREYS_ABOVE = 10


def base_usage_class_from_code(usage_code: str | None) -> str | None:
    """usage_code（3桁文字列）から規模条件反映前の基礎 usage_class を返す。

    未知のコード・None は None を返す（呼び出し側で "other" 等に丸める）。
    """
    if usage_code is None:
        return None
    code = str(usage_code).strip()
    if not code:
        return None
    # 先頭3桁のみを見る（末尾に枝番が付くケースへの耐性）
    code3 = code[:3]
    return USAGE_CODE_TABLE.get(code3)


def determine_usage_class(
    usage_code: str | None,
    *,
    total_floor_area_m2: float | None = None,
    storeys_above: int | None = None,
    hospital_flag: bool = False,
    welfare_flag: bool = False,
    station_hint: bool = False,
    datacenter_hint: bool = False,
    public_hint: bool = False,
) -> str:
    """usage_class を決定する（純 Python、GIS 非依存）。

    引数:
      usage_code: PLATEAU bldg:usage コード（3桁文字列想定）。
      total_floor_area_m2: 延床面積（規模条件の判定に使用）。
      storeys_above: 地上階数（residential_large 判定に使用）。
      hospital_flag / welfare_flag / station_hint / datacenter_hint / public_hint:
        外部データ（P04/P14/N02 等、40_context.py で算出）との空間結合結果に
        基づく上書きヒント。usage_code だけでは判別できない用途分類を補う。

    優先順位（上のヒントほど強い）:
      1. hospital_flag -> "hospital"
      2. datacenter_hint -> "datacenter"
      3. station_hint -> "station"
      4. welfare_flag -> "welfare"
      5. public_hint -> "public_critical"
      6. usage_code 由来の基礎クラス + 規模条件
      7. 上記いずれでも決まらない場合は "other"
    """
    if hospital_flag:
        return "hospital"
    if datacenter_hint:
        return "datacenter"
    if station_hint:
        return "station"
    if welfare_flag:
        return "welfare"
    if public_hint:
        return "public_critical"

    base = base_usage_class_from_code(usage_code)
    if base is None:
        return "other"

    if base == "commercial":
        if total_floor_area_m2 is not None and total_floor_area_m2 >= COMMERCIAL_LARGE_FLOOR_AREA_M2:
            return "commercial_large"
        return "commercial"

    if base == "residential":
        is_large = False
        if total_floor_area_m2 is not None and total_floor_area_m2 >= RESIDENTIAL_LARGE_FLOOR_AREA_M2:
            is_large = True
        if storeys_above is not None and storeys_above >= RESIDENTIAL_LARGE_STOREYS_ABOVE:
            is_large = True
        return "residential_large" if is_large else "residential"

    return base
