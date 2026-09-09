'use strict';

// node --test web/tests/  （Node 22 標準の node:test / node:assert のみ使用、外部パッケージ不可）

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  priorityBase,
  isLowConfidenceFlagged,
  isUnassessed,
  priorityColor,
  priorityColorForAssessment,
  priorityLabelForAssessment,
  gradeColor,
  statusLabel,
  usageClassLabel,
  joinBuildingsWithAssessments,
  filterFeatures,
  searchFeatures,
  PRIORITY_COLORS,
  PRIORITY_UNKNOWN_COLOR,
  PRIORITY_UNASSESSED_COLOR,
  UNASSESSED_LABEL,
  GRADE_UNKNOWN_COLOR,
} = require('../lib/join.js');

// --- テスト用の最小フィクスチャ -----------------------------------------

function makeBuilding(id, props) {
  return {
    type: 'Feature',
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]] },
    properties: Object.assign({ building_id: id }, props),
  };
}

function makeAssessment(id, props) {
  return Object.assign(
    {
      building_id: id,
      tier: 0,
      score_version: '0.1.0',
      data_version: 'test',
      computed_at: '2026-09-09T00:00:00Z',
      status: 'assessed',
      H: 2,
      V: 2,
      I: 2,
      P: 2,
      C: 60,
      priority: 'C',
      priority_raised_by_low_confidence: false,
      evidence: [],
      missing_info: [],
      priority_checks: [],
      measures: [],
    },
    props
  );
}

// --- priorityBase / isLowConfidenceFlagged ------------------------------

test('priorityBase strips the "*" low-confidence marker', () => {
  assert.equal(priorityBase('A'), 'A');
  assert.equal(priorityBase('B*'), 'B');
  assert.equal(priorityBase(null), null);
  assert.equal(priorityBase(undefined), null);
});

test('isLowConfidenceFlagged detects the "*" suffix only', () => {
  assert.equal(isLowConfidenceFlagged('B*'), true);
  assert.equal(isLowConfidenceFlagged('B'), false);
  assert.equal(isLowConfidenceFlagged(null), false);
});

// --- priorityColor -------------------------------------------------------

test('priorityColor maps A/B/C/D per spec (A=red B=orange C=yellow D=gray)', () => {
  assert.equal(priorityColor('A'), PRIORITY_COLORS.A);
  assert.equal(priorityColor('B'), PRIORITY_COLORS.B);
  assert.equal(priorityColor('C'), PRIORITY_COLORS.C);
  assert.equal(priorityColor('D'), PRIORITY_COLORS.D);
});

test('priorityColor ignores the "*" suffix (same color as base grade)', () => {
  assert.equal(priorityColor('A*'), priorityColor('A'));
  assert.equal(priorityColor('B*'), priorityColor('B'));
});

test('priorityColor falls back to the unknown color for null/unrecognized values', () => {
  assert.equal(priorityColor(null), PRIORITY_UNKNOWN_COLOR);
  assert.equal(priorityColor(undefined), PRIORITY_UNKNOWN_COLOR);
  assert.equal(priorityColor('Z'), PRIORITY_UNKNOWN_COLOR);
});

// --- gradeColor ------------------------------------------------------------

test('gradeColor returns the unknown color for null/undefined/non-numeric values', () => {
  assert.equal(gradeColor('H', null), GRADE_UNKNOWN_COLOR);
  assert.equal(gradeColor('V', undefined), GRADE_UNKNOWN_COLOR);
  assert.equal(gradeColor('I', 'n/a'), GRADE_UNKNOWN_COLOR);
  assert.equal(gradeColor('C', NaN), GRADE_UNKNOWN_COLOR);
});

test('gradeColor is monotonic and distinct across the 0-4 scale for H/V/I', () => {
  const colors = [0, 1, 2, 3, 4].map((v) => gradeColor('H', v));
  const distinct = new Set(colors);
  assert.equal(distinct.size, 5, 'each of the 5 H grades should have a distinct color');
  // V and I share the same ramp as H
  assert.equal(gradeColor('V', 3), gradeColor('H', 3));
  assert.equal(gradeColor('I', 0), gradeColor('H', 0));
});

test('gradeColor clamps out-of-range H/V/I values into the 0-4 ramp', () => {
  assert.equal(gradeColor('H', -1), gradeColor('H', 0));
  assert.equal(gradeColor('H', 9), gradeColor('H', 4));
});

test('gradeColor buckets C (confidence 0-100) into 5 bands at the documented boundaries', () => {
  assert.equal(gradeColor('C', 0), gradeColor('C', 19));
  assert.notEqual(gradeColor('C', 19), gradeColor('C', 20));
  assert.equal(gradeColor('C', 20), gradeColor('C', 39));
  assert.notEqual(gradeColor('C', 39), gradeColor('C', 40));
  assert.equal(gradeColor('C', 80), gradeColor('C', 100));
});

// --- isUnassessed / priorityColorForAssessment / priorityLabelForAssessment ----
// TASK-008: status = insufficient_data（priority null）は除外せず「評価不能」として
// 明示表示する。D（現状対応不要）の灰色とは区別できる色・別ラベルにする。

test('isUnassessed is true only for status=insufficient_data with a null priority', () => {
  assert.equal(isUnassessed(makeAssessment('b', { status: 'insufficient_data', priority: null, H: null, P: null })), true);
  assert.equal(isUnassessed(makeAssessment('b', { status: 'assessed', priority: 'C' })), false);
  assert.equal(isUnassessed(makeAssessment('b', { status: 'out_of_scope', priority: null })), false);
  assert.equal(isUnassessed(null), false);
  assert.equal(isUnassessed(undefined), false);
});

test('priorityColorForAssessment uses PRIORITY_UNASSESSED_COLOR for insufficient_data, distinct from D and from unknown', () => {
  const unassessed = makeAssessment('b', { status: 'insufficient_data', priority: null, H: null, P: null });
  assert.equal(priorityColorForAssessment(unassessed), PRIORITY_UNASSESSED_COLOR);
  assert.notEqual(PRIORITY_UNASSESSED_COLOR, PRIORITY_COLORS.D);
  assert.notEqual(PRIORITY_UNASSESSED_COLOR, PRIORITY_UNKNOWN_COLOR);
});

test('priorityColorForAssessment falls back to priorityColor()-equivalent behavior for other statuses', () => {
  const assessed = makeAssessment('b', { status: 'assessed', priority: 'A' });
  assert.equal(priorityColorForAssessment(assessed), priorityColor('A'));
  const outOfScope = makeAssessment('b', { status: 'out_of_scope', priority: null });
  assert.equal(priorityColorForAssessment(outOfScope), PRIORITY_UNKNOWN_COLOR);
  assert.equal(priorityColorForAssessment(null), priorityColor(null));
});

test('priorityLabelForAssessment returns the 評価不能 label for insufficient_data, and leaves out_of_scope unchanged', () => {
  const unassessed = makeAssessment('b', { status: 'insufficient_data', priority: null, H: null, P: null });
  assert.equal(priorityLabelForAssessment(unassessed), UNASSESSED_LABEL);
  assert.equal(priorityLabelForAssessment(unassessed), '評価不能（データ不足）');

  const outOfScope = makeAssessment('b', { status: 'out_of_scope', priority: null });
  assert.equal(priorityLabelForAssessment(outOfScope), statusLabel('out_of_scope'));

  const assessed = makeAssessment('b', { status: 'assessed', priority: 'B*' });
  assert.equal(priorityLabelForAssessment(assessed), 'B*');

  assert.equal(priorityLabelForAssessment(null), statusLabel(null));
});

// --- statusLabel / usageClassLabel -----------------------------------------

test('statusLabel maps the three defined statuses to Japanese labels', () => {
  assert.equal(statusLabel('assessed'), '評価済み');
  assert.equal(statusLabel('insufficient_data'), 'データ不足（一次評価不能）');
  assert.equal(statusLabel('out_of_scope'), '評価対象外');
});

test('statusLabel falls back to the raw value for unknown status codes', () => {
  assert.equal(statusLabel('something_new'), 'something_new');
});

test('usageClassLabel maps known usage_class codes and falls back otherwise', () => {
  assert.equal(usageClassLabel('hospital'), '病院・救急');
  assert.equal(usageClassLabel('unknown_code'), 'unknown_code');
  assert.equal(usageClassLabel(null), '不明');
});

// --- joinBuildingsWithAssessments -------------------------------------------

test('joinBuildingsWithAssessments attaches the matching assessment by building_id', () => {
  const buildings = {
    type: 'FeatureCollection',
    features: [makeBuilding('bldg_a', { name: 'A' }), makeBuilding('bldg_b', { name: 'B' })],
  };
  const assessments = [makeAssessment('bldg_a', { priority: 'A' }), makeAssessment('bldg_b', { priority: 'D' })];

  const result = joinBuildingsWithAssessments(buildings, assessments);

  assert.equal(result.type, 'FeatureCollection');
  assert.equal(result.features.length, 2);
  assert.equal(result.features[0].properties.assessment.priority, 'A');
  assert.equal(result.features[1].properties.assessment.priority, 'D');
  assert.deepEqual(result.unmatchedAssessments, []);
});

test('joinBuildingsWithAssessments sets assessment to null when no match exists', () => {
  const buildings = { type: 'FeatureCollection', features: [makeBuilding('bldg_a', { name: 'A' })] };
  const result = joinBuildingsWithAssessments(buildings, []);
  assert.equal(result.features[0].properties.assessment, null);
});

test('joinBuildingsWithAssessments reports assessments with no matching building as unmatched', () => {
  const buildings = { type: 'FeatureCollection', features: [makeBuilding('bldg_a', { name: 'A' })] };
  const assessments = [makeAssessment('bldg_a'), makeAssessment('bldg_ghost')];
  const result = joinBuildingsWithAssessments(buildings, assessments);
  assert.equal(result.unmatchedAssessments.length, 1);
  assert.equal(result.unmatchedAssessments[0].building_id, 'bldg_ghost');
});

test('joinBuildingsWithAssessments does not mutate its inputs', () => {
  const buildings = { type: 'FeatureCollection', features: [makeBuilding('bldg_a', { name: 'A' })] };
  const assessments = [makeAssessment('bldg_a', { priority: 'A' })];
  const buildingsCopy = JSON.parse(JSON.stringify(buildings));
  const assessmentsCopy = JSON.parse(JSON.stringify(assessments));

  joinBuildingsWithAssessments(buildings, assessments);

  assert.deepEqual(buildings, buildingsCopy);
  assert.deepEqual(assessments, assessmentsCopy);
});

test('joinBuildingsWithAssessments rejects a non-FeatureCollection input', () => {
  assert.throws(() => joinBuildingsWithAssessments({}, []), TypeError);
  assert.throws(() => joinBuildingsWithAssessments(null, []), TypeError);
});

// --- filterFeatures ----------------------------------------------------------

function sampleJoined() {
  const buildings = {
    type: 'FeatureCollection',
    features: [
      makeBuilding('b1', { name: 'One', usage_class: 'hospital' }),
      makeBuilding('b2', { name: 'Two', usage_class: 'office' }),
      makeBuilding('b3', { name: 'Three', usage_class: 'office' }),
    ],
  };
  const assessments = [
    makeAssessment('b1', { priority: 'A', priority_raised_by_low_confidence: false }),
    makeAssessment('b2', { priority: 'B*', priority_raised_by_low_confidence: true }),
    makeAssessment('b3', { priority: 'B', priority_raised_by_low_confidence: false }),
  ];
  return joinBuildingsWithAssessments(buildings, assessments).features;
}

/** sampleJoined() に status=insufficient_data（評価不能）の建物を1件加えたもの。 */
function sampleJoinedWithUnassessed() {
  const buildings = {
    type: 'FeatureCollection',
    features: [
      makeBuilding('b1', { name: 'One', usage_class: 'hospital' }),
      makeBuilding('b2', { name: 'Two', usage_class: 'office' }),
      makeBuilding('b3', { name: 'Three', usage_class: 'office' }),
      makeBuilding('b4', { name: 'Four', usage_class: 'office' }),
    ],
  };
  const assessments = [
    makeAssessment('b1', { priority: 'A', priority_raised_by_low_confidence: false }),
    makeAssessment('b2', { priority: 'B*', priority_raised_by_low_confidence: true }),
    makeAssessment('b3', { priority: 'B', priority_raised_by_low_confidence: false }),
    makeAssessment('b4', {
      status: 'insufficient_data',
      priority: null,
      H: null,
      P: null,
      priority_raised_by_low_confidence: false,
    }),
  ];
  return joinBuildingsWithAssessments(buildings, assessments).features;
}

test('filterFeatures filters by usageClass', () => {
  const result = filterFeatures(sampleJoined(), { usageClass: 'office' });
  assert.equal(result.length, 2);
  assert.ok(result.every((f) => f.properties.usage_class === 'office'));
});

test('filterFeatures filters by priority base grade, ignoring the "*" marker', () => {
  const result = filterFeatures(sampleJoined(), { priority: 'B' });
  assert.equal(result.length, 2); // b2 ("B*") and b3 ("B")
});

test('filterFeatures priority="unassessed" keeps only insufficient_data buildings (TASK-008)', () => {
  const result = filterFeatures(sampleJoinedWithUnassessed(), { priority: 'unassessed' });
  assert.equal(result.length, 1);
  assert.equal(result[0].properties.building_id, 'b4');
  assert.equal(result[0].properties.assessment.status, 'insufficient_data');
});

test('filterFeatures needsReviewOnly keeps only priority_raised_by_low_confidence === true', () => {
  const result = filterFeatures(sampleJoined(), { needsReviewOnly: true });
  assert.equal(result.length, 1);
  assert.equal(result[0].properties.building_id, 'b2');
});

test('filterFeatures with "all"/no filters returns everything unchanged', () => {
  const all = sampleJoined();
  const result = filterFeatures(all, { usageClass: 'all', priority: 'all', needsReviewOnly: false });
  assert.equal(result.length, all.length);
});

test('filterFeatures combines multiple conditions (AND)', () => {
  const result = filterFeatures(sampleJoined(), { usageClass: 'office', priority: 'B', needsReviewOnly: true });
  assert.equal(result.length, 1);
  assert.equal(result[0].properties.building_id, 'b2');
});

// --- searchFeatures ------------------------------------------------------------

test('searchFeatures matches by name substring, case-insensitively', () => {
  const result = searchFeatures(sampleJoined(), 'tWo');
  assert.equal(result.length, 1);
  assert.equal(result[0].properties.building_id, 'b2');
});

test('searchFeatures matches by building_id substring', () => {
  const result = searchFeatures(sampleJoined(), 'b3');
  assert.equal(result.length, 1);
  assert.equal(result[0].properties.building_id, 'b3');
});

test('searchFeatures returns all features for an empty/blank query', () => {
  const all = sampleJoined();
  assert.equal(searchFeatures(all, '').length, all.length);
  assert.equal(searchFeatures(all, '   ').length, all.length);
});

// --- サンプルデータでの結合（web/data/*.sample 実ファイル） ------------------------

test('sample data: buildings_sample.geojson and assessments_sample.json join cleanly', () => {
  const dataDir = path.join(__dirname, '..', 'data');
  const buildings = JSON.parse(fs.readFileSync(path.join(dataDir, 'buildings_sample.geojson'), 'utf8'));
  const assessments = JSON.parse(fs.readFileSync(path.join(dataDir, 'assessments_sample.json'), 'utf8'));

  assert.equal(buildings.type, 'FeatureCollection');
  assert.ok(Array.isArray(assessments));
  assert.equal(buildings.features.length, assessments.length);

  const result = joinBuildingsWithAssessments(buildings, assessments);

  assert.equal(result.features.length, buildings.features.length);
  assert.deepEqual(result.unmatchedAssessments, []);
  assert.ok(
    result.features.every((f) => f.properties.assessment !== null),
    'every sample building should have a matching assessment'
  );

  // TASK-008: out_of_scope・insufficient_data（評価不能）は priority が null で許容される。
  // それ以外（assessed）の建物は A/B/C/D のいずれかの色を持つ。
  result.features.forEach((f) => {
    const a = f.properties.assessment;
    if (a.status === 'out_of_scope' || a.status === 'insufficient_data') {
      assert.equal(a.priority, null);
      return;
    }
    assert.ok(['A', 'B', 'C', 'D'].includes(priorityBase(a.priority)), `unexpected priority ${a.priority}`);
    assert.notEqual(priorityColor(a.priority), PRIORITY_UNKNOWN_COLOR);
  });

  // insufficient_data（評価不能）が少なくとも1件含まれ、D とは別の色で塗られる（TASK-008）。
  const unassessedFeatures = result.features.filter((f) => isUnassessed(f.properties.assessment));
  assert.ok(unassessedFeatures.length > 0, 'sample data should include at least one insufficient_data (評価不能) building');
  unassessedFeatures.forEach((f) => {
    assert.equal(priorityColorForAssessment(f.properties.assessment), PRIORITY_UNASSESSED_COLOR);
    assert.equal(priorityLabelForAssessment(f.properties.assessment), UNASSESSED_LABEL);
  });

  // サンプルには少なくとも1件、確信度不足による優先度繰り上げ（"*"）が含まれる
  const flagged = result.features.filter((f) => isLowConfidenceFlagged(f.properties.assessment.priority));
  assert.ok(flagged.length > 0, 'sample data should include at least one "*"-flagged building for the 要確認 filter');

  // 実在施設名を含まないことの簡易チェック（架空マーカー "サンプル" を含む）
  result.features.forEach((f) => {
    assert.ok(f.properties.name && f.properties.name.indexOf('サンプル') !== -1);
  });
});

test('sample data: needsReviewOnly filter isolates the "*" flagged sample buildings', () => {
  const dataDir = path.join(__dirname, '..', 'data');
  const buildings = JSON.parse(fs.readFileSync(path.join(dataDir, 'buildings_sample.geojson'), 'utf8'));
  const assessments = JSON.parse(fs.readFileSync(path.join(dataDir, 'assessments_sample.json'), 'utf8'));
  const joined = joinBuildingsWithAssessments(buildings, assessments).features;

  const flagged = filterFeatures(joined, { needsReviewOnly: true });
  assert.ok(flagged.length > 0);
  assert.ok(flagged.every((f) => f.properties.assessment.priority_raised_by_low_confidence === true));
});
