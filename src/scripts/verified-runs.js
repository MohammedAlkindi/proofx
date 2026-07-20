(function () {
  var panels = Array.prototype.slice.call(document.querySelectorAll('[data-run-artifact]'));
  var lists = Array.prototype.slice.call(document.querySelectorAll('[data-run-summary-list]'));
  if (!panels.length && !lists.length) return;

  fetch('/verified-runs.json')
    .then(function (response) {
      return response.ok ? response.json() : Promise.reject(new Error('missing artifact'));
    })
    .then(function (bundle) {
      var runs = Array.isArray(bundle.runs) ? bundle.runs : [];
      panels.forEach(function (panel) {
        renderPanel(panel, findRun(runs, panel.getAttribute('data-run-artifact')));
      });
      lists.forEach(function (list) {
        renderSummaryList(list, runs);
      });
    })
    .catch(function () {
      panels.forEach(function (panel) {
        panel.innerHTML = '<p class="muted">No verified run artifact is available yet.</p>';
      });
      lists.forEach(function (list) {
        list.innerHTML = '<p class="muted">No verified run artifact is available yet.</p>';
      });
    });

  function findRun(runs, engine) {
    var needle = String(engine || '').toLowerCase();
    return runs.find(function (run) {
      return String(run.engine || '').toLowerCase() === needle;
    });
  }

  function renderPanel(panel, run) {
    if (!run) {
      panel.innerHTML = '<p class="muted">No artifact found for this engine.</p>';
      return;
    }

    var metrics = Object.keys(run.metrics || {}).slice(0, 5).map(function (key) {
      return metricTile(labelize(key), formatValue(run.metrics[key]));
    }).join('');

    var bounds = Object.keys(run.bounds || {}).map(function (key) {
      return '<span class="tag">' + escapeHtml(labelize(key)) + ': ' +
        escapeHtml(formatValue(run.bounds[key])) + '</span>';
    }).join('');

    panel.innerHTML = [
      '<div class="verified-run__meta">',
      '<span class="badge">' + escapeHtml(run.claim_level || 'run') + '</span>',
      '<span class="badge">' + escapeHtml(run.status || 'unknown') + '</span>',
      '<span class="badge">seed ' + escapeHtml(String(run.seed)) + '</span>',
      commitBadge(run.commit),
      '</div>',
      '<p class="verified-run__summary">' + escapeHtml(run.summary || '') + '</p>',
      '<div class="metric-grid verified-run__metrics">' + metrics + '</div>',
      '<div class="verified-run__bounds">' + bounds + '</div>',
      provenance(run.environment),
      '<details class="verified-run__details">',
      '<summary>Reproduce this run</summary>',
      '<pre class="code-block"><code>' + escapeHtml(run.reproduce || '') + '</code></pre>',
      '</details>',
    ].join('');
  }

  // The artifact records the environment its numbers came from. Rendering it
  // matters most when it is incomplete: an unresolved dependency means the
  // snapshot cannot support the reproducibility claim, and a reader who cannot
  // see that has no way to tell a full record from an empty one.
  function provenance(environment) {
    if (!environment) return '';

    var unresolved = Array.isArray(environment.dependencies_unresolved)
      ? environment.dependencies_unresolved
      : [];
    var deps = environment.dependencies || {};
    var names = Object.keys(deps).sort();

    var rows = names.map(function (name) {
      return '<li><code>' + escapeHtml(name) + '</code> ' + escapeHtml(deps[name]) + '</li>';
    }).join('');

    var warning = '';
    if (unresolved.length) {
      warning = '<p class="verified-run__provenance-warn">Incomplete dependency snapshot: ' +
        'this artifact was built in an environment that could not resolve ' +
        escapeHtml(unresolved.join(', ')) +
        '. Treat its dependency record as partial.</p>';
    }

    return [
      '<details class="verified-run__details verified-run__provenance">',
      '<summary>Environment provenance' +
        (unresolved.length ? ' <span class="tag tag--warn">incomplete</span>' : '') +
        '</summary>',
      warning,
      '<ul class="verified-run__env">',
      '<li><code>python</code> ' + escapeHtml(environment.python || 'unknown') + '</li>',
      '<li><code>platform</code> ' + escapeHtml(environment.platform || 'unknown') + '</li>',
      '</ul>',
      names.length
        ? '<ul class="verified-run__env">' + rows + '</ul>'
        : '<p class="muted">No dependency versions were resolved.</p>',
      '</details>',
    ].join('');
  }

  function renderSummaryList(list, runs) {
    if (!runs.length) {
      list.innerHTML = '<p class="muted">No runs were recorded in the artifact bundle.</p>';
      return;
    }
    list.innerHTML = runs.map(function (run) {
      return [
        '<article class="card verified-run-card">',
        '<div class="verified-run-card__head">',
        '<h3>' + escapeHtml(run.engine || 'Engine') + '</h3>',
        '<span class="badge">' + escapeHtml(run.claim_level || 'run') + '</span>',
        '</div>',
        '<p>' + escapeHtml(run.summary || '') + '</p>',
        '<p class="muted">Status: <code>' + escapeHtml(run.status || 'unknown') +
        '</code> · commit ' + escapeHtml(commitText(run.commit)) + '</p>',
        provenance(run.environment),
        '</article>',
      ].join('');
    }).join('');
  }

  function metricTile(label, value) {
    return '<div class="metric-card"><div class="metric-card__val">' + escapeHtml(value) +
      '</div><div class="metric-card__label">' + escapeHtml(label) + '</div></div>';
  }

  function commitBadge(commit) {
    return '<span class="badge">commit ' + escapeHtml(commitText(commit)) + '</span>';
  }

  function commitText(commit) {
    if (!commit || !commit.sha) return 'unknown';
    return String(commit.sha).slice(0, 12) + (commit.dirty ? ' + local edits' : '');
  }

  function labelize(value) {
    return String(value).replace(/_/g, ' ');
  }

  function formatValue(value) {
    if (typeof value === 'number') {
      if (Number.isInteger(value)) return value.toLocaleString();
      return value.toFixed(4);
    }
    if (value === null || typeof value === 'undefined') return 'n/a';
    return String(value);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      var entities = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      };
      return entities[char] || char;
    });
  }
}());
