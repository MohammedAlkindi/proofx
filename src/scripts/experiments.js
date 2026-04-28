/**
 * experiments.js — inline ledger viewer for any page that includes
 * <div id="experiments-viewer"></div>
 *
 * Data sources (tried in order):
 *  1. /results.json  — pre-generated summary from --output-json flag
 *  2. File drag-and-drop / browse — user loads a .jsonl ledger locally
 *
 * Renders a filterable, sortable table of near-miss candidates.
 * Works as an ES module; imported by main.js.
 */

const MOUNT_ID = 'experiments-viewer';

function init() {
  const mount = document.getElementById(MOUNT_ID);
  if (!mount) return;

  mount.innerHTML = buildShell();
  wireControls(mount);

  // Try to auto-load from /results.json
  fetch('/results.json')
    .then(r => (r.ok ? r.json() : Promise.reject()))
    .then(data => {
      const entries = [
        ...(data.top_collatz || []).map(e => ({ ...e, conjecture: 'collatz' })),
        ...(data.top_goldbach || []).map(e => ({ ...e, conjecture: 'goldbach' })),
      ];
      if (entries.length) loadEntries(mount, entries, 'results.json');
    })
    .catch(() => {
      showDropZone(mount);
    });
}

function buildShell() {
  return `
<style>
  #${MOUNT_ID} {
    --ev-bg: var(--surface-1, rgba(255,255,255,.04));
    --ev-border: var(--border, rgba(128,128,128,.2));
    --ev-accent: var(--accent, #6366f1);
    --ev-muted: var(--muted, rgba(255,255,255,.5));
    font-size: .85rem;
  }
  .ev-toolbar {
    display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
    padding: .75rem 0; margin-bottom: .5rem;
    border-bottom: 1px solid var(--ev-border);
  }
  .ev-toolbar label { display:flex; align-items:center; gap:6px; color:var(--ev-muted); }
  .ev-toolbar select, .ev-toolbar input[type=range] {
    background: var(--ev-bg); border: 1px solid var(--ev-border);
    color: inherit; border-radius: 5px; padding: 4px 7px;
    font: inherit; cursor: pointer;
  }
  .ev-toolbar .ev-btn {
    background: var(--ev-accent); color:#fff; border:none; border-radius:6px;
    padding: 5px 12px; cursor:pointer; font:inherit; font-size:.8rem; font-weight:600;
  }
  .ev-toolbar .ev-btn:hover { opacity:.85; }
  .ev-stats {
    font-size:.78rem; color:var(--ev-muted); margin-bottom:.75rem;
    display:flex; gap:16px; flex-wrap:wrap;
  }
  .ev-stats b { color:inherit; filter:brightness(1.6); }
  .ev-drop {
    border: 2px dashed var(--ev-border); border-radius:10px;
    padding: 40px; text-align:center; color:var(--ev-muted);
    cursor:pointer; transition: border-color .2s;
    margin: 1rem 0;
  }
  .ev-drop.over { border-color: var(--ev-accent); }
  .ev-drop p { margin-top:8px; font-size:.78rem; }
  .ev-table-wrap { overflow-x:auto; }
  .ev-table { width:100%; border-collapse:collapse; font-size:.82rem; }
  .ev-table th {
    text-align:left; padding:7px 10px;
    border-bottom:2px solid var(--ev-border);
    color:var(--ev-accent); font-weight:600; cursor:pointer;
    user-select:none; white-space:nowrap;
  }
  .ev-table th:hover { opacity:.8; }
  .ev-table th.asc::after { content:' ↑'; }
  .ev-table th.desc::after { content:' ↓'; }
  .ev-table td { padding:6px 10px; border-bottom:1px solid var(--ev-border); }
  .ev-table tr:hover td { background:var(--ev-bg); }
  .ev-pill {
    display:inline-block; border-radius:4px; padding:1px 7px;
    font-size:.72rem; font-weight:600;
  }
  .ev-pill-collatz { background:rgba(91,156,246,.15); color:#5b9cf6; }
  .ev-pill-goldbach { background:rgba(249,115,22,.15); color:#f97316; }
  .ev-score { font-weight:600; }
  .ev-score-hi { color:#ef4444; }
  .ev-score-mid { color:#eab308; }
  .ev-score-lo { color:#22c55e; }
  .ev-empty { text-align:center; padding:32px; color:var(--ev-muted); }
  .ev-source-tag {
    font-size:.72rem; color:var(--ev-muted); margin-left:auto;
    font-style:italic;
  }
</style>
<div class="ev-toolbar" id="ev-toolbar" style="display:none">
  <label>Conjecture
    <select id="ev-filter-conj">
      <option value="all">All</option>
      <option value="collatz">Collatz</option>
      <option value="goldbach">Goldbach</option>
    </select>
  </label>
  <label>Min score &ge; <span id="ev-score-val">0.00</span>
    <input type="range" id="ev-min-score" min="0" max="1" step="0.01" value="0">
  </label>
  <label>Show top
    <select id="ev-top-k">
      <option value="25">25</option>
      <option value="50" selected>50</option>
      <option value="100">100</option>
      <option value="0">All</option>
    </select>
  </label>
  <span class="ev-source-tag" id="ev-source-tag"></span>
  <button class="ev-btn" onclick="document.getElementById('ev-file-input').click()">Load JSONL</button>
  <input type="file" id="ev-file-input" accept=".jsonl,.json" style="display:none">
</div>
<div class="ev-stats" id="ev-stats" style="display:none"></div>
<div id="ev-drop" class="ev-drop" style="display:none"
  ondragover="event.preventDefault();this.classList.add('over')"
  ondragleave="this.classList.remove('over')"
  ondrop="event.preventDefault();this.classList.remove('over');window._evHandleDrop(event)">
  <div style="font-size:28px">📂</div>
  <p>Drop a <code>.jsonl</code> ledger file here, or click the button above to browse</p>
  <p style="font-size:.72rem;margin-top:4px">Generated via <code>python -m codebase.cli falsify --save-ledger out.jsonl</code></p>
</div>
<div id="ev-table-wrap" class="ev-table-wrap" style="display:none">
  <table class="ev-table">
    <thead>
      <tr>
        <th data-col="rank">#</th>
        <th data-col="candidate">Candidate</th>
        <th data-col="conjecture">Conjecture</th>
        <th data-col="near_miss_score" class="desc">Near-miss score</th>
        <th data-col="strategy">Strategy</th>
      </tr>
    </thead>
    <tbody id="ev-tbody"></tbody>
  </table>
  <p id="ev-empty" class="ev-empty" style="display:none">No entries match current filters.</p>
</div>`;
}

function wireControls(mount) {
  // Sort state
  let sortCol = 'near_miss_score';
  let sortDir = -1;
  let allEntries = [];

  // Expose for the drop handler (can't close over due to ondrop attribute)
  window._evHandleDrop = e => {
    const file = e.dataTransfer.files[0];
    if (file) readJSONL(file, mount, entries => loadEntries(mount, entries, file.name));
  };

  mount.querySelector('#ev-file-input').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) readJSONL(file, mount, entries => loadEntries(mount, entries, file.name));
    e.target.value = '';
  });

  mount.querySelector('#ev-filter-conj').addEventListener('change', () => render(mount));
  mount.querySelector('#ev-top-k').addEventListener('change', () => render(mount));
  mount.querySelector('#ev-min-score').addEventListener('input', function () {
    mount.querySelector('#ev-score-val').textContent = parseFloat(this.value).toFixed(2);
    render(mount);
  });

  mount.querySelectorAll('.ev-table th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (col === 'rank') return;
      if (sortCol === col) sortDir *= -1;
      else { sortCol = col; sortDir = -1; }
      mount.querySelectorAll('.ev-table th').forEach(h => h.classList.remove('asc', 'desc'));
      th.classList.add(sortDir === -1 ? 'desc' : 'asc');
      render(mount);
    });
  });

  // Attach state to mount element so render() can read it
  mount._ev = { allEntries, sortCol: () => sortCol, sortDir: () => sortDir };

  // Override loadEntries to also update closure state
  mount._evLoad = entries => {
    allEntries.length = 0;
    entries.forEach(e => allEntries.push(e));
    mount._ev.allEntries = allEntries;
    render(mount);
  };
}

function loadEntries(mount, entries, sourceName) {
  document.getElementById('ev-drop').style.display = 'none';
  document.getElementById('ev-toolbar').style.display = 'flex';
  document.getElementById('ev-stats').style.display = 'flex';
  document.getElementById('ev-table-wrap').style.display = 'block';
  const tag = document.getElementById('ev-source-tag');
  if (tag) tag.textContent = sourceName ? `source: ${sourceName}` : '';
  mount._evLoad(entries);
}

function showDropZone(mount) {
  document.getElementById('ev-drop').style.display = 'block';
  document.getElementById('ev-toolbar').style.display = 'flex';
}

function render(mount) {
  const state = mount._ev;
  if (!state) return;

  const conj = document.getElementById('ev-filter-conj').value;
  const minScore = parseFloat(document.getElementById('ev-min-score').value) || 0;
  const topK = parseInt(document.getElementById('ev-top-k').value) || Infinity;
  const col = state.sortCol();
  const dir = state.sortDir();

  const filtered = state.allEntries.filter(e =>
    (conj === 'all' || e.conjecture === conj) && (e.near_miss_score || 0) >= minScore
  );
  const sorted = [...filtered].sort((a, b) => {
    const av = a[col] ?? 0, bv = b[col] ?? 0;
    if (typeof av === 'string') return dir * av.localeCompare(bv);
    return dir * (bv - av);
  });
  const slice = topK === Infinity ? sorted : sorted.slice(0, topK);

  // Stats bar
  const all = state.allEntries;
  const maxScore = all.reduce((m, e) => Math.max(m, e.near_miss_score || 0), 0);
  document.getElementById('ev-stats').innerHTML =
    `<span>Total: <b>${all.length.toLocaleString()}</b></span>` +
    `<span>Showing: <b>${slice.length.toLocaleString()}</b></span>` +
    `<span>Collatz: <b>${all.filter(e => e.conjecture === 'collatz').length.toLocaleString()}</b></span>` +
    `<span>Goldbach: <b>${all.filter(e => e.conjecture === 'goldbach').length.toLocaleString()}</b></span>` +
    `<span>Max score: <b>${maxScore.toFixed(4)}</b></span>`;

  // Table
  const tbody = document.getElementById('ev-tbody');
  const empty = document.getElementById('ev-empty');
  if (!slice.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  tbody.innerHTML = slice.map((e, i) => {
    const s = e.near_miss_score || 0;
    const cls = s >= 0.75 ? 'ev-score-hi' : s >= 0.4 ? 'ev-score-mid' : 'ev-score-lo';
    const conj = e.conjecture || 'unknown';
    return `<tr>
      <td style="color:var(--ev-muted)">${i + 1}</td>
      <td><b>${(e.candidate || 0).toLocaleString()}</b></td>
      <td><span class="ev-pill ev-pill-${conj}">${conj}</span></td>
      <td><span class="ev-score ${cls}">${s.toFixed(4)}</span></td>
      <td style="color:var(--ev-muted);font-size:.78rem">${e.strategy || '—'}</td>
    </tr>`;
  }).join('');
}

function readJSONL(file, mount, cb) {
  const reader = new FileReader();
  reader.onload = evt => {
    const lines = evt.target.result.split('\n').filter(l => l.trim());
    const entries = [];
    for (const line of lines) {
      try { entries.push(JSON.parse(line)); } catch (_) {}
    }
    if (!entries.length) { alert('No valid entries found.'); return; }
    cb(entries);
  };
  reader.readAsText(file);
}

// Auto-init when the DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
