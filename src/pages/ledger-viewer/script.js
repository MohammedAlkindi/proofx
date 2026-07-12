(function () {
  var allEntries = [];
  var sortCol = 'near_miss_score';
  var sortDir = -1; // -1 = desc
  var expandedRow = null;

  // ── File loading ────────────────────────────────────────────────────────────
  document.getElementById('load-btn').addEventListener('click', function () {
    document.getElementById('file-input').click();
  });
  document.getElementById('file-input').addEventListener('change', function (e) {
    var file = e.target.files[0];
    if (file) loadFile(file);
  });

  var dropZone = document.getElementById('drop-zone');
  dropZone.addEventListener('click', function () { document.getElementById('file-input').click(); });
  dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', function () {
    dropZone.classList.remove('drag-over');
  });
  dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    var file = e.dataTransfer.files[0];
    if (file) loadFile(file);
  });

  function loadFile(file) {
    var reader = new FileReader();
    reader.onload = function (evt) {
      var lines = evt.target.result.split('\n').filter(function (l) { return l.trim(); });
      allEntries = [];
      for (var i = 0; i < lines.length; i++) {
        try { allEntries.push(JSON.parse(lines[i])); } catch (_) {}
      }
      if (allEntries.length === 0) {
        alert('No valid JSONL entries found in the file.');
        return;
      }
      document.getElementById('drop-zone').hidden = true;
      document.getElementById('table-container').hidden = false;
      document.getElementById('stats-bar').hidden = false;
      render();
    };
    reader.readAsText(file);
  }

  // ── Filtering & sorting ─────────────────────────────────────────────────────
  document.getElementById('filter-conjecture').addEventListener('change', render);
  document.getElementById('top-k').addEventListener('change', render);
  document.getElementById('min-score').addEventListener('input', function () {
    document.getElementById('min-score-val').textContent = parseFloat(this.value).toFixed(2);
    render();
  });

  document.querySelectorAll('thead th[data-col]').forEach(function (th) {
    th.addEventListener('click', function () {
      var col = th.dataset.col;
      if (col === 'rank') return;
      if (sortCol === col) { sortDir *= -1; }
      else { sortCol = col; sortDir = -1; }
      document.querySelectorAll('thead th').forEach(function (h) { h.classList.remove('sort-asc', 'sort-desc'); });
      th.classList.add(sortDir === -1 ? 'sort-desc' : 'sort-asc');
      render();
    });
  });

  function getFiltered() {
    var conj = document.getElementById('filter-conjecture').value;
    var minScore = parseFloat(document.getElementById('min-score').value);
    return allEntries.filter(function (e) {
      return (conj === 'all' || e.conjecture === conj) && e.near_miss_score >= minScore;
    });
  }

  function render() {
    var filtered = getFiltered();
    var topK = parseInt(document.getElementById('top-k').value, 10) || Infinity;

    var sorted = filtered.slice().sort(function (a, b) {
      var av = a[sortCol] != null ? a[sortCol] : 0;
      var bv = b[sortCol] != null ? b[sortCol] : 0;
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * (bv - av);
    });

    var slice = topK === Infinity ? sorted : sorted.slice(0, topK);

    updateStats(filtered, slice);
    renderRows(slice);
  }

  function updateStats(filtered, slice) {
    var collatz = allEntries.filter(function (e) { return e.conjecture === 'collatz'; }).length;
    var goldbach = allEntries.filter(function (e) { return e.conjecture === 'goldbach'; }).length;
    var max = allEntries.reduce(function (m, e) { return Math.max(m, e.near_miss_score); }, 0);
    document.getElementById('stat-total').textContent = allEntries.length.toLocaleString();
    document.getElementById('stat-showing').textContent = slice.length.toLocaleString();
    document.getElementById('stat-collatz').textContent = collatz.toLocaleString();
    document.getElementById('stat-goldbach').textContent = goldbach.toLocaleString();
    document.getElementById('stat-max').textContent = max.toFixed(4);
  }

  function renderRows(entries) {
    var tbody = document.getElementById('ledger-body');
    tbody.innerHTML = '';
    expandedRow = null;

    if (entries.length === 0) {
      document.getElementById('empty-msg').hidden = false;
      return;
    }
    document.getElementById('empty-msg').hidden = true;

    entries.forEach(function (e, i) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td class="ledger-rank">' + (i + 1) + '</td>' +
        '<td><b>' + e.candidate.toLocaleString() + '</b></td>' +
        '<td>' + conjPill(e.conjecture) + '</td>' +
        '<td>' + scoreBar(e.near_miss_score) + '</td>' +
        '<td class="ledger-muted-cell">' + e.strategy + '</td>' +
        '<td class="ledger-muted-cell">' + fmtTime(e.timestamp) + '</td>';
      tr.addEventListener('click', function () { toggleDetail(tr, e); });
      tbody.appendChild(tr);
    });
  }

  function toggleDetail(tr, entry) {
    if (expandedRow && expandedRow !== tr) {
      expandedRow.classList.remove('expanded');
      var old = expandedRow.nextSibling;
      if (old && old.classList.contains('detail-row')) old.remove();
    }

    if (tr.classList.contains('expanded')) {
      tr.classList.remove('expanded');
      var next = tr.nextSibling;
      if (next && next.classList.contains('detail-row')) next.remove();
      expandedRow = null;
      return;
    }

    tr.classList.add('expanded');
    expandedRow = tr;

    var detail = document.createElement('tr');
    detail.classList.add('detail-row');
    var td = document.createElement('td');
    td.colSpan = 6;
    td.innerHTML = buildDetail(entry);
    detail.appendChild(td);
    tr.insertAdjacentElement('afterend', detail);
  }

  function buildDetail(e) {
    var features = e.features || {};
    var details = e.details || {};

    var featureItems = Object.keys(features).map(function (k) {
      var v = features[k];
      return '<div class="ledger-feature-item"><div class="key">' + k.replace(/_/g, ' ') + '</div><div class="val">' +
        (typeof v === 'number' ? v.toFixed(5) : v) + '</div></div>';
    }).join('');

    var detailItems = Object.keys(details).map(function (k) {
      var v = details[k];
      return '<span><span>' + k.replace(/_/g, ' ') + '</span> <b>' +
        (typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(4) : v) + '</b></span>';
    }).join('');

    return (
      '<div class="ledger-detail-panel">' +
        '<h3>Feature vector</h3>' +
        '<div class="ledger-feature-grid">' + (featureItems || '<span class="muted">none</span>') + '</div>' +
        '<h3>Diagnostics</h3>' +
        '<div class="ledger-details-kv">' + (detailItems || '<span class="muted">none</span>') + '</div>' +
        '<div class="ledger-seed-line">RNG seed: <b>' + e.rng_seed + '</b> &nbsp;|&nbsp; Strategy: <b>' + e.strategy + '</b></div>' +
      '</div>'
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function conjPill(c) {
    return '<span class="ledger-pill ledger-pill--' + c + '">' + c + '</span>';
  }

  function scoreColor(s) {
    if (s >= 0.75) return 'var(--ledger-score-high)';
    if (s >= 0.40) return 'var(--ledger-score-mid)';
    return 'var(--ledger-score-low)';
  }

  function scoreBar(s) {
    var col = scoreColor(s);
    return (
      '<div class="ledger-score-bar">' +
        '<span class="ledger-score-num" style="color:' + col + '">' + s.toFixed(4) + '</span>' +
        '<span class="ledger-score-track"><span class="ledger-score-fill" style="width:' + (s * 100).toFixed(1) + '%;background:' + col + '"></span></span>' +
      '</div>'
    );
  }

  function fmtTime(ts) {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleTimeString();
  }

  // ── CSV export ──────────────────────────────────────────────────────────────
  document.getElementById('export-btn').addEventListener('click', function () {
    if (allEntries.length === 0) return;
    var rows = [['candidate', 'conjecture', 'near_miss_score', 'strategy', 'timestamp', 'rng_seed']];
    getFiltered().forEach(function (e) {
      rows.push([e.candidate, e.conjecture, e.near_miss_score, e.strategy, e.timestamp, e.rng_seed]);
    });
    var csv = rows.map(function (r) { return r.join(','); }).join('\n');
    var a = document.createElement('a');
    a.href = 'data:text/csv,' + encodeURIComponent(csv);
    a.download = 'proofx_ledger.csv';
    a.click();
  });
}());
