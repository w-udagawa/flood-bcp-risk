/**
 * web/app.js
 *
 * TASK-005 静的ビューア試作。地図表示・レイヤ切替・フィルタ・検索・建物カルテ描画を行う。
 * データ結合と色/ラベルの純ロジックは web/lib/join.js（window.FloodBcpJoin）に分離し、
 * ここではその関数を呼び出して DOM / MapLibre GL JS を操作する。
 *
 * 参照仕様: docs/02_要件定義書.md 第7・11章、docs/03_スコアリング仕様.md 第8〜13章
 * 免責（NFR-08）: 本表示はオープンデータによる一次スクリーニングであり、安全性を保証するものではありません。
 *
 * 未検証事項: 本環境ではブラウザでの動作確認ができていない（node --check による構文チェックのみ）。
 * web/README.md を参照。
 */
(function () {
  'use strict';

  var J = window.FloodBcpJoin;

  var GSI_PALE_TILE_URL = 'https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png';
  var GSI_ATTRIBUTION =
    '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル（淡色地図）</a>';

  var DATA_URLS = {
    buildings: 'data/buildings_sample.geojson',
    assessments: 'data/assessments_sample.json',
    measures: 'data/measures.json',
  };

  // アプリ状態
  var state = {
    joinedFeatures: [], // FloodBcpJoin.joinBuildingsWithAssessments() の features（フル）
    measuresById: {}, // { "M-01": { id, title, condition } }
    filters: { usageClass: 'all', priority: 'all', needsReviewOnly: false },
    searchQuery: '',
    layer: 'priority', // 'priority' | 'H' | 'V' | 'I' | 'C'
    selectedBuildingId: null,
    map: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  // ---------------------------------------------------------------------
  // データ読込
  // ---------------------------------------------------------------------

  function loadJson(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) {
        throw new Error('failed to load ' + url + ' (HTTP ' + res.status + ')');
      }
      return res.json();
    });
  }

  function init() {
    Promise.all([loadJson(DATA_URLS.buildings), loadJson(DATA_URLS.assessments), loadJson(DATA_URLS.measures)])
      .then(function (results) {
        var buildings = results[0];
        var assessments = results[1];
        var measures = results[2];

        var joined = J.joinBuildingsWithAssessments(buildings, assessments);
        if (joined.unmatchedAssessments.length > 0 && window.console) {
          console.warn('building_id が buildings 側に見つからない assessment があります:', joined.unmatchedAssessments);
        }
        state.joinedFeatures = joined.features;

        (measures.measures || []).forEach(function (m) {
          state.measuresById[m.id] = m;
        });

        populateUsageOptions(state.joinedFeatures);
        bindControls();
        initMap(state.joinedFeatures);
        renderLegend();
        refresh();
      })
      .catch(function (err) {
        renderLoadError(err);
      });
  }

  function renderLoadError(err) {
    var mapWrap = byId('map-wrap');
    if (mapWrap) {
      var el = document.createElement('div');
      el.style.padding = '16px';
      el.style.color = '#b30000';
      el.textContent = 'データ読み込みに失敗しました: ' + (err && err.message ? err.message : String(err));
      mapWrap.appendChild(el);
    }
    if (window.console) console.error(err);
  }

  // ---------------------------------------------------------------------
  // フィルタ UI の初期化
  // ---------------------------------------------------------------------

  function populateUsageOptions(features) {
    var select = byId('usage-select');
    var seen = Object.create(null);
    var codes = [];
    features.forEach(function (f) {
      var code = f.properties.usage_class;
      if (code && !seen[code]) {
        seen[code] = true;
        codes.push(code);
      }
    });
    codes.sort();
    codes.forEach(function (code) {
      var opt = document.createElement('option');
      opt.value = code;
      opt.textContent = J.usageClassLabel(code) + '（' + code + '）';
      select.appendChild(opt);
    });
  }

  function bindControls() {
    byId('search-input').addEventListener('input', function (e) {
      state.searchQuery = e.target.value;
      refresh();
    });
    byId('usage-select').addEventListener('change', function (e) {
      state.filters.usageClass = e.target.value;
      refresh();
    });
    byId('priority-select').addEventListener('change', function (e) {
      state.filters.priority = e.target.value;
      refresh();
    });
    byId('needs-review-checkbox').addEventListener('change', function (e) {
      state.filters.needsReviewOnly = !!e.target.checked;
      refresh();
    });

    var radios = document.querySelectorAll('input[name="layer"]');
    for (var i = 0; i < radios.length; i++) {
      radios[i].addEventListener('change', function (e) {
        if (e.target.checked) {
          state.layer = e.target.value;
          renderLegend();
          refresh();
        }
      });
    }
  }

  // ---------------------------------------------------------------------
  // 絞り込み → 地図・一覧の再描画
  // ---------------------------------------------------------------------

  function currentlyVisibleFeatures() {
    var filtered = J.filterFeatures(state.joinedFeatures, state.filters);
    return J.searchFeatures(filtered, state.searchQuery);
  }

  /** 表示用に properties を平坦化した GeoJSON FeatureCollection を作る（MapLibre のスタイル式で扱いやすくするため）。 */
  function toDisplayGeojson(features, layer) {
    return {
      type: 'FeatureCollection',
      features: features.map(function (f) {
        var props = f.properties;
        var a = props.assessment;
        var fillColor = colorForLayer(layer, a);
        var emphasized = a ? J.isLowConfidenceFlagged(a.priority) : false;
        return {
          type: 'Feature',
          geometry: f.geometry,
          properties: {
            building_id: props.building_id,
            name: props.name,
            usage_class: props.usage_class,
            status: a ? a.status : null,
            priority: a ? a.priority : null,
            fill_color: fillColor,
            emphasized: emphasized,
          },
        };
      }),
    };
  }

  function colorForLayer(layer, assessment) {
    if (!assessment) return layer === 'priority' ? J.PRIORITY_UNKNOWN_COLOR : J.GRADE_UNKNOWN_COLOR;
    if (layer === 'priority') return J.priorityColor(assessment.priority);
    return J.gradeColor(layer, assessment[layer]);
  }

  function refresh() {
    var visible = currentlyVisibleFeatures();
    updateMapData(visible);
    renderBuildingList(visible);
  }

  // ---------------------------------------------------------------------
  // 地図（MapLibre GL JS）
  // ---------------------------------------------------------------------

  function initMap(allFeatures) {
    var map = new maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          gsi_pale: {
            type: 'raster',
            tiles: [GSI_PALE_TILE_URL],
            tileSize: 256,
            attribution: GSI_ATTRIBUTION,
          },
        },
        layers: [{ id: 'gsi_pale', type: 'raster', source: 'gsi_pale' }],
      },
      center: [139.669, 35.6075], // 自由が丘駅周辺（架空サンプルの中心。実施設ではない）
      zoom: 16,
      attributionControl: true,
    });
    state.map = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

    map.on('load', function () {
      map.addSource('buildings', { type: 'geojson', data: toDisplayGeojson(allFeatures, state.layer) });

      map.addLayer({
        id: 'buildings-fill',
        type: 'fill',
        source: 'buildings',
        paint: {
          'fill-color': ['get', 'fill_color'],
          'fill-opacity': 0.75,
        },
      });

      map.addLayer({
        id: 'buildings-outline',
        type: 'line',
        source: 'buildings',
        paint: {
          'line-color': ['case', ['get', 'emphasized'], '#1f2530', '#4a5568'],
          'line-width': ['case', ['get', 'emphasized'], 3, 1],
        },
      });

      map.on('click', 'buildings-fill', function (e) {
        if (!e.features || e.features.length === 0) return;
        selectBuilding(e.features[0].properties.building_id);
      });
      map.on('mouseenter', 'buildings-fill', function () {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'buildings-fill', function () {
        map.getCanvas().style.cursor = '';
      });

      // 初期表示：全建物にフィットさせる（15件程度の想定）
      fitToFeatures(allFeatures);
    });
  }

  function fitToFeatures(features) {
    if (!state.map || features.length === 0) return;
    var minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
    features.forEach(function (f) {
      var ring = f.geometry && f.geometry.coordinates && f.geometry.coordinates[0];
      if (!ring) return;
      ring.forEach(function (pt) {
        if (pt[0] < minLon) minLon = pt[0];
        if (pt[0] > maxLon) maxLon = pt[0];
        if (pt[1] < minLat) minLat = pt[1];
        if (pt[1] > maxLat) maxLat = pt[1];
      });
    });
    if (minLon === Infinity) return;
    state.map.fitBounds(
      [
        [minLon, minLat],
        [maxLon, maxLat],
      ],
      { padding: 60, duration: 0 }
    );
  }

  function updateMapData(visibleFeatures) {
    if (!state.map) return;
    var source = state.map.getSource('buildings');
    if (!source) return; // まだ map load 前
    source.setData(toDisplayGeojson(visibleFeatures, state.layer));
  }

  // ---------------------------------------------------------------------
  // 凡例
  // ---------------------------------------------------------------------

  function renderLegend() {
    var el = byId('legend');
    var html = '';
    if (state.layer === 'priority') {
      html += '<h3>対応優先度</h3>';
      [
        ['A', '優先現地調査'],
        ['B', '簡易診断推奨'],
        ['C', '定期確認'],
        ['D', '現状対応不要'],
      ].forEach(function (pair) {
        html +=
          '<div class="row"><span class="chip" style="background:' +
          J.priorityColor(pair[0]) +
          '"></span>' +
          pair[0] +
          '：' +
          pair[1] +
          '</div>';
      });
      html += '<div class="row"><span class="chip emphasis" style="background:#fff"></span>枠線強調＝確信度不足による繰り上げ（*）</div>';
      html += '<div class="row"><span class="chip" style="background:' + J.PRIORITY_UNKNOWN_COLOR + '"></span>評価対象外・未評価</div>';
    } else {
      var labels = { H: 'ハザード等級 H', V: '流入脆弱性等級 V', I: '事業影響度等級 I', C: 'データ確信度 C' };
      html += '<h3>' + labels[state.layer] + '</h3>';
      if (state.layer === 'C') {
        [
          [0, '0〜19'],
          [20, '20〜39'],
          [40, '40〜59'],
          [60, '60〜79'],
          [80, '80〜100'],
        ].forEach(function (pair) {
          html += '<div class="row"><span class="chip" style="background:' + J.gradeColor('C', pair[0]) + '"></span>' + pair[1] + '</div>';
        });
      } else {
        [0, 1, 2, 3, 4].forEach(function (v) {
          html += '<div class="row"><span class="chip" style="background:' + J.gradeColor(state.layer, v) + '"></span>等級 ' + v + '</div>';
        });
      }
      html += '<div class="row"><span class="chip" style="background:' + J.GRADE_UNKNOWN_COLOR + '"></span>データなし</div>';
    }
    el.innerHTML = html;
  }

  // ---------------------------------------------------------------------
  // 該当建物一覧
  // ---------------------------------------------------------------------

  function renderBuildingList(features) {
    byId('result-count').textContent = features.length + ' 件';
    var list = byId('building-list');
    list.innerHTML = '';
    features.forEach(function (f) {
      var props = f.properties;
      var a = props.assessment;
      var li = document.createElement('li');
      li.dataset.buildingId = props.building_id;

      var left = document.createElement('span');
      var swatch = document.createElement('span');
      swatch.className = 'swatch';
      swatch.style.background = a ? J.priorityColor(a.priority) : J.PRIORITY_UNKNOWN_COLOR;
      left.appendChild(swatch);
      left.appendChild(document.createTextNode(props.name || props.building_id));

      var right = document.createElement('span');
      right.style.color = '#5b6472';
      right.textContent = a && a.priority ? a.priority : J.statusLabel(a ? a.status : null);

      li.appendChild(left);
      li.appendChild(right);
      li.addEventListener('click', function () {
        selectBuilding(props.building_id);
      });
      list.appendChild(li);
    });
  }

  // ---------------------------------------------------------------------
  // 建物カルテ（サイドパネル）
  // ---------------------------------------------------------------------

  function findFullFeature(buildingId) {
    for (var i = 0; i < state.joinedFeatures.length; i++) {
      if (state.joinedFeatures[i].properties.building_id === buildingId) return state.joinedFeatures[i];
    }
    return null;
  }

  function selectBuilding(buildingId) {
    state.selectedBuildingId = buildingId;
    var feature = findFullFeature(buildingId);
    if (!feature) return;
    renderSidePanel(feature);
    if (state.map) {
      fitToFeatures([feature]);
    }
  }

  function escapeHtml(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function gradeCell(label, value) {
    return (
      '<div class="cell"><div class="k">' +
      escapeHtml(label) +
      '</div><div class="v">' +
      (value === null || value === undefined ? '—' : escapeHtml(value)) +
      '</div></div>'
    );
  }

  function renderSidePanel(feature) {
    var props = feature.properties;
    var a = props.assessment;
    var panel = byId('side-panel');

    var priorityHtml = '';
    if (a && a.priority) {
      priorityHtml =
        '<span class="priority-badge" style="background:' +
        J.priorityColor(a.priority) +
        '">' +
        escapeHtml(a.priority) +
        '</span>';
      if (J.isLowConfidenceFlagged(a.priority)) {
        priorityHtml += ' <span style="font-size:11px;color:#5b6472;">※確信度不足のため優先度を繰り上げ表示</span>';
      }
    } else {
      priorityHtml = '<span class="priority-badge" style="background:' + J.PRIORITY_UNKNOWN_COLOR + ';color:#333;">—</span>';
    }
    var statusHtml = '<span class="status-badge">' + escapeHtml(J.statusLabel(a ? a.status : null)) + '</span>';

    var gradesHtml =
      '<div class="grade-grid">' +
      gradeCell('H', a ? a.H : null) +
      gradeCell('V', a ? a.V : null) +
      gradeCell('I', a ? a.I : null) +
      gradeCell('P', a ? a.P : null) +
      '</div>' +
      '<div style="font-size:12px;color:#5b6472;">データ確信度 C：' +
      (a && a.C !== null && a.C !== undefined ? escapeHtml(a.C) + ' / 100' : '—') +
      '</div>';

    var evidenceRows = ((a && a.evidence) || [])
      .map(function (ev) {
        return (
          '<tr><td>' +
          escapeHtml(ev.axis) +
          '</td><td>' +
          escapeHtml(ev.rule) +
          '</td><td>' +
          escapeHtml(ev.value) +
          '</td><td>' +
          escapeHtml(ev.source) +
          '</td><td>' +
          escapeHtml(ev.fetched_at) +
          '</td></tr>'
        );
      })
      .join('');
    var evidenceHtml =
      '<table class="evidence-table"><thead><tr><th>等級</th><th>根拠</th><th>入力値</th><th>出典</th><th>取得日</th></tr></thead><tbody>' +
      (evidenceRows || '<tr><td colspan="5" style="color:#5b6472;">根拠情報なし</td></tr>') +
      '</tbody></table>';

    var missingHtml = listOrNone((a && a.missing_info) || []);
    var checksHtml = listOrNone((a && a.priority_checks) || []);

    var measuresHtml = ((a && a.measures) || [])
      .map(function (mid) {
        var m = state.measuresById[mid];
        return (
          '<div class="measure-item"><span class="mid">' +
          escapeHtml(mid) +
          '</span> ' +
          escapeHtml(m ? m.title : '（メニュー未定義）') +
          '</div>'
        );
      })
      .join('');

    panel.innerHTML =
      '<h2>' +
      escapeHtml(props.name || '（名称未設定）') +
      '</h2>' +
      '<div class="sub">' +
      escapeHtml(props.address || '住所不明') +
      '<br/>building_id: ' +
      escapeHtml(props.building_id) +
      '</div>' +
      '<div style="margin-bottom:10px;">' +
      priorityHtml +
      statusHtml +
      '</div>' +
      gradesHtml +
      '<section><h3>評価根拠</h3>' +
      evidenceHtml +
      '</section>' +
      '<section><h3>不足情報</h3>' +
      missingHtml +
      '</section>' +
      '<section><h3>優先確認事項</h3>' +
      checksHtml +
      '</section>' +
      '<section><h3>対策候補</h3>' +
      (measuresHtml || '<div style="color:#5b6472;">現時点で提示条件に該当する対策候補はありません。</div>') +
      '</section>' +
      '<section><h3>簡易診断</h3>' +
      '<div style="color:#5b6472;">Tier 1（12問）の簡易診断フォームは本試作（静的ビューア）には未実装です。フェーズ2で非公開層（api/）とあわせて実装予定。</div>' +
      '</section>';
  }

  function listOrNone(items) {
    if (!items || items.length === 0) {
      return '<div style="color:#5b6472;">なし</div>';
    }
    return (
      '<ul class="plain-list">' +
      items
        .map(function (item) {
          return '<li>' + escapeHtml(item) + '</li>';
        })
        .join('') +
      '</ul>'
    );
  }

  // ---------------------------------------------------------------------

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
