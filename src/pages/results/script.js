(function () {
  var DATA_SECTIONS = ['run-stats', 'collatz-results', 'goldbach-results'];

  fetch('/results.json')
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (data) {
      DATA_SECTIONS.forEach(showSection);
      document.getElementById('results-source-note').textContent =
        'This page overlays live data from /results.json.';

      populateStats(data);

      populateTable(
        document.querySelector('[aria-label="CollatzX near-miss candidates"] tbody'),
        data.top_collatz || [],
        function (e) {
          var details = e.details || {};
          return [
            Number(e.candidate).toLocaleString(),
            Number(e.near_miss_score).toFixed(4),
            details.stopping_time != null ? Number(details.stopping_time).toLocaleString() : 'n/a',
            details.max_value != null ? Number(details.max_value).toLocaleString() : 'n/a',
            e.strategy || 'n/a'
          ];
        }
      );
      buildBarChart(document.getElementById('collatz-chart'), data.top_collatz || []);

      populateTable(
        document.querySelector('[aria-label="GoldbachX partition deficit candidates"] tbody'),
        data.top_goldbach || [],
        function (e) {
          var features = e.features || {};
          return [
            Number(e.candidate).toLocaleString(),
            features.expected_partitions != null ? Math.round(features.expected_partitions).toLocaleString() : 'n/a',
            features.actual_partitions != null ? Math.round(features.actual_partitions).toLocaleString() : 'n/a',
            Number(e.near_miss_score).toFixed(4),
            e.strategy || 'n/a'
          ];
        }
      );
      buildBarChart(document.getElementById('goldbach-chart'), data.top_goldbach || []);

      var badge = document.querySelector('[data-live-badge]');
      if (badge) badge.hidden = false;
    })
    .catch(function () {
      document.getElementById('empty-state').hidden = false;
      document.getElementById('results-source-note').textContent =
        'No generated results found. See "Reproduce A Run" below.';
    });

  function showSection(id) {
    var el = document.getElementById(id);
    if (el) el.hidden = false;
  }

  function populateTable(tbody, entries, rowFn) {
    if (!tbody || !entries.length) return;
    tbody.innerHTML = entries.map(function (e, i) {
      return '<tr><td>' + (i + 1) + '</td>' +
        rowFn(e).map(function (v) { return '<td>' + v + '</td>'; }).join('') +
        '</tr>';
    }).join('');
  }

  function populateStats(data) {
    var grid = document.getElementById('run-stats-grid');
    if (!grid || !data.stats) return;
    var stats = data.stats;
    var tiles = [
      ['Seed', data.seed],
      ['Budget', data.budget],
      ['Collatz evaluated', stats.collatz_evaluated],
      ['Goldbach evaluated', stats.goldbach_evaluated],
      ['Max Collatz near-miss', typeof stats.collatz_max_near_miss === 'number' ? stats.collatz_max_near_miss.toFixed(4) : 'n/a'],
      ['Max Goldbach near-miss', typeof stats.goldbach_max_near_miss === 'number' ? stats.goldbach_max_near_miss.toFixed(4) : 'n/a'],
      ['Elapsed', typeof stats.elapsed_s === 'number' ? stats.elapsed_s.toFixed(2) + 's' : 'n/a']
    ];
    grid.innerHTML = tiles.map(function (t) {
      return '<div class="metric-card"><div class="metric-card__val">' + t[1] +
        '</div><div class="metric-card__label">' + t[0] + '</div></div>';
    }).join('');
  }

  // Small dependency-free horizontal bar chart, top 10 entries by near_miss_score.
  function buildBarChart(container, entries) {
    if (!container || !entries.length) return;
    var top = entries.slice().sort(function (a, b) {
      return b.near_miss_score - a.near_miss_score;
    }).slice(0, 10);
    var max = top.reduce(function (m, e) { return Math.max(m, e.near_miss_score); }, 0) || 1;

    container.innerHTML = top.map(function (e) {
      var pct = ((e.near_miss_score / max) * 100).toFixed(1);
      var label = Number(e.candidate).toLocaleString();
      return (
        '<div class="bar-chart__row">' +
          '<span class="bar-chart__label">' + label + '</span>' +
          '<span class="bar-chart__track"><span class="bar-chart__fill" style="width:' + pct + '%"></span></span>' +
          '<span class="bar-chart__value">' + e.near_miss_score.toFixed(4) + '</span>' +
        '</div>'
      );
    }).join('');
  }
}());
