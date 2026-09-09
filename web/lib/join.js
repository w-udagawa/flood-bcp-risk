/**
 * web/lib/join.js
 *
 * 建物ポリゴン（buildings.geojson）と評価結果（assessments.json）を
 * building_id で結合する純関数、および地図・カルテ表示用の色/ラベル関数。
 *
 * ブラウザ（<script src="lib/join.js"></script> → window.FloodBcpJoin）と
 * Node.js（require('./join.js')、node --test 用）の両方から使えるよう
 * UMD 風の単純なパターンで公開する。外部パッケージには依存しない。
 *
 * 参照仕様: docs/02_要件定義書.md 第7・9・11章、docs/03_スコアリング仕様.md 第8〜13章
 */
(function (root, factory) {
  var mod = factory();
  if (typeof module === 'object' && module.exports) {
    // Node.js / node --test
    module.exports = mod;
  }
  if (root) {
    // ブラウザ: window.FloodBcpJoin として公開
    root.FloodBcpJoin = mod;
  }
})(typeof window !== 'undefined' ? window : typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // ---------------------------------------------------------------------
  // 色定義（docs/03_スコアリング仕様.md 第9章、TASK-005 指示に基づく）
  // ---------------------------------------------------------------------

  // 優先度 A/B/C/D の塗り分け（A=赤 B=橙 C=黄 D=灰）
  var PRIORITY_COLORS = {
    A: '#d7263d',
    B: '#f46a25',
    C: '#f4c542',
    D: '#9aa0a6',
  };
  // 評価対象外・未評価（priority が null など）
  var PRIORITY_UNKNOWN_COLOR = '#dfe3e8';

  // H/V/I（0〜4）用の順序尺度カラーランプ（薄→濃、5段階）
  var GRADE_RAMP_0_4 = ['#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000'];
  // C（確信度 0〜100）用のカラーランプ（薄→濃、5段階）
  var CONFIDENCE_RAMP = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
  // 値が null/undefined の場合の中立色（H/V/I/C 共通）
  var GRADE_UNKNOWN_COLOR = '#e5e7eb';

  var STATUS_LABELS = {
    assessed: '評価済み',
    insufficient_data: 'データ不足（一次評価不能）',
    out_of_scope: '評価対象外',
  };

  var USAGE_CLASS_LABELS = {
    hospital: '病院・救急',
    station: '駅・駅施設',
    datacenter: 'データセンター',
    public_critical: '庁舎・防災拠点',
    commercial_large: '大規模商業施設',
    commercial: '商業施設',
    office: '事務所',
    welfare: '福祉施設',
    logistics: '物流施設',
    school: '学校',
    residential_large: '大規模集合住宅',
    residential: '住宅',
    other: 'その他',
  };

  /**
   * priority 文字列（例 "B*"）から確信度フラグの "*" を除いた基底等級を返す。
   * null/undefined は null を返す。
   */
  function priorityBase(priority) {
    if (priority === null || priority === undefined) return null;
    var s = String(priority);
    return s.charAt(0);
  }

  /**
   * priority 文字列に確信度による繰り上げ（"*"）が付いているかどうか。
   * docs/03_スコアリング仕様.md 第9章「確信度ルール」。
   */
  function isLowConfidenceFlagged(priority) {
    if (priority === null || priority === undefined) return false;
    return String(priority).indexOf('*') !== -1;
  }

  /** 優先度 A/B/C/D（"*" は無視）に対応する塗り色を返す。 */
  function priorityColor(priority) {
    var base = priorityBase(priority);
    if (base === null) return PRIORITY_UNKNOWN_COLOR;
    return PRIORITY_COLORS[base] || PRIORITY_UNKNOWN_COLOR;
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  /**
   * H/V/I/C の等級値から塗り色を返す。
   * axis: 'H' | 'V' | 'I' | 'C'
   * value: 数値（H/V/I は 0〜4、C は 0〜100）または null/undefined
   */
  function gradeColor(axis, value) {
    if (value === null || value === undefined || typeof value !== 'number' || isNaN(value)) {
      return GRADE_UNKNOWN_COLOR;
    }
    if (axis === 'C') {
      var idx = value < 20 ? 0 : value < 40 ? 1 : value < 60 ? 2 : value < 80 ? 3 : 4;
      return CONFIDENCE_RAMP[idx];
    }
    // H / V / I: 0〜4 の整数尺度
    var i = clamp(Math.round(value), 0, 4);
    return GRADE_RAMP_0_4[i];
  }

  /** status コードから日本語ラベルを返す。未知の値はそのまま返す。 */
  function statusLabel(status) {
    return STATUS_LABELS[status] || status || '不明';
  }

  /** usage_class コードから日本語ラベルを返す。未知の値はそのまま返す。 */
  function usageClassLabel(usageClass) {
    if (usageClass === null || usageClass === undefined) return '不明';
    return USAGE_CLASS_LABELS[usageClass] || usageClass;
  }

  // ---------------------------------------------------------------------
  // 結合ロジック
  // ---------------------------------------------------------------------

  /**
   * buildings GeoJSON（FeatureCollection）の properties.building_id をキーに
   * assessments 配列を引き当てる。
   *
   * - 各 Feature を複製し、properties.assessment に対応する評価結果（無ければ null）を格納する。
   * - assessments 側の building_id が buildings 側に存在しない場合は unmatchedAssessments に集める。
   * - 入力は変更しない（純関数）。
   *
   * @param {object} buildingsGeojson - FeatureCollection（properties.building_id を持つ Feature 群）
   * @param {Array<object>} assessments - assessment オブジェクトの配列（building_id を持つ）
   * @returns {{type: 'FeatureCollection', features: Array<object>, unmatchedAssessments: Array<object>}}
   */
  function joinBuildingsWithAssessments(buildingsGeojson, assessments) {
    if (!buildingsGeojson || !Array.isArray(buildingsGeojson.features)) {
      throw new TypeError('buildingsGeojson must be a FeatureCollection with a features array');
    }
    var list = Array.isArray(assessments) ? assessments : [];

    var byId = Object.create(null);
    var usedIds = Object.create(null);
    list.forEach(function (a) {
      if (a && a.building_id !== undefined && a.building_id !== null) {
        byId[a.building_id] = a;
      }
    });

    var features = buildingsGeojson.features.map(function (feature) {
      var props = feature && feature.properties ? feature.properties : {};
      var buildingId = props.building_id;
      var assessment = Object.prototype.hasOwnProperty.call(byId, buildingId) ? byId[buildingId] : null;
      if (assessment) usedIds[buildingId] = true;
      return {
        type: 'Feature',
        geometry: feature.geometry,
        properties: Object.assign({}, props, { assessment: assessment }),
      };
    });

    var unmatchedAssessments = list.filter(function (a) {
      return !a || a.building_id === undefined || a.building_id === null || !usedIds[a.building_id];
    });

    return {
      type: 'FeatureCollection',
      features: features,
      unmatchedAssessments: unmatchedAssessments,
    };
  }

  // ---------------------------------------------------------------------
  // フィルタ・検索（FR-05・FR-06、TASK-005 の縮小版：用途・優先度・要確認のみ）
  // ---------------------------------------------------------------------

  /**
   * 結合済み Feature 配列を条件で絞り込む。
   * @param {Array<object>} features - joinBuildingsWithAssessments() の features
   * @param {object} filters
   * @param {string} [filters.usageClass] - 'all' または usage_class 値
   * @param {string} [filters.priority] - 'all' または 'A'|'B'|'C'|'D'（"*" の有無は問わない）
   * @param {boolean} [filters.needsReviewOnly] - true の場合、確信度不足で優先度が繰り上げられた
   *   （priority_raised_by_low_confidence === true、表記上 "*" が付く）建物のみを残す。
   *   docs/03_スコアリング仕様.md 第9章「確信度ルール」に基づく。
   */
  function filterFeatures(features, filters) {
    var f = filters || {};
    var usageClass = f.usageClass && f.usageClass !== 'all' ? f.usageClass : null;
    var priority = f.priority && f.priority !== 'all' ? f.priority : null;
    var needsReviewOnly = !!f.needsReviewOnly;

    return (features || []).filter(function (feature) {
      var props = feature.properties || {};
      var assessment = props.assessment;

      if (usageClass && props.usage_class !== usageClass) return false;

      if (priority) {
        var base = assessment ? priorityBase(assessment.priority) : null;
        if (base !== priority) return false;
      }

      if (needsReviewOnly) {
        var flagged = assessment ? !!assessment.priority_raised_by_low_confidence : false;
        if (!flagged) return false;
      }

      return true;
    });
  }

  /**
   * 名称（name）または building_id の部分一致で検索する（大文字小文字を無視）。
   * 空文字・空白のみのクエリは全件を返す。
   */
  function searchFeatures(features, query) {
    var q = (query || '').trim().toLowerCase();
    if (!q) return (features || []).slice();
    return (features || []).filter(function (feature) {
      var props = feature.properties || {};
      var name = (props.name || '').toLowerCase();
      var id = (props.building_id || '').toLowerCase();
      return name.indexOf(q) !== -1 || id.indexOf(q) !== -1;
    });
  }

  return {
    PRIORITY_COLORS: PRIORITY_COLORS,
    PRIORITY_UNKNOWN_COLOR: PRIORITY_UNKNOWN_COLOR,
    GRADE_UNKNOWN_COLOR: GRADE_UNKNOWN_COLOR,
    priorityBase: priorityBase,
    isLowConfidenceFlagged: isLowConfidenceFlagged,
    priorityColor: priorityColor,
    gradeColor: gradeColor,
    statusLabel: statusLabel,
    usageClassLabel: usageClassLabel,
    joinBuildingsWithAssessments: joinBuildingsWithAssessments,
    filterFeatures: filterFeatures,
    searchFeatures: searchFeatures,
  };
});
