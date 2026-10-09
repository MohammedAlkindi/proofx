"use strict";
(() => {
    const base = '/experiments/gb-001/';
    const status = document.getElementById('experiment-status');
    const seedSelect = document.getElementById('experiment-seed');
    const rows = document.getElementById('experiment-rows');
    const candidateRows = document.getElementById('candidate-rows');
    let manifest;
    let request = 0;
    function cell(row, value) {
        row.insertCell().textContent = value;
    }
    async function inspect(run) {
        const current = ++request;
        const panel = document.getElementById('candidate-inspector');
        const message = document.getElementById('candidate-status');
        panel.hidden = false;
        message.textContent = `Loading ${run.policy}, seed ${run.seed}…`;
        candidateRows.replaceChildren();
        try {
            const response = await fetch(base + encodeURIComponent(run.ledger));
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            const entries = (await response.text()).trim().split('\n').map(line => JSON.parse(line));
            if (current !== request)
                return;
            entries.forEach((entry, i) => {
                const tr = document.createElement('tr');
                [String(i + 1), entry.candidate.toLocaleString(), String(entry.actual_partitions),
                    entry.expected_partitions.toFixed(4), entry.ratio.toFixed(4),
                    entry.witness ? entry.witness.join(' + ') : 'None found'].forEach(value => cell(tr, value));
                candidateRows.append(tr);
            });
            message.textContent = `${entries.length} candidates · ${run.policy} · seed ${run.seed}`;
            document.getElementById('candidate-caption').textContent = `${run.policy}, seed ${run.seed}: evaluation order`;
            panel.scrollIntoView({ block: 'start' });
        }
        catch {
            if (current === request)
                message.textContent = 'Could not load this ledger. Download the complete bundle to inspect it locally.';
        }
    }
    function visibleRuns() {
        return manifest.runs.filter(run => seedSelect.value === 'all' || String(run.seed) === seedSelect.value);
    }
    function render() {
        rows.replaceChildren();
        visibleRuns().forEach(run => {
            const tr = document.createElement('tr');
            [run.policy, String(run.seed), String(run.rare_hits), `${(run.rare_recall * 100).toFixed(1)}%`,
                run.min_ratio.toFixed(4), run.median_candidate.toLocaleString(), run.elapsed_s.toFixed(4)]
                .forEach(value => cell(tr, value));
            const td = tr.insertCell();
            const button = document.createElement('button');
            button.className = 'btn btn--sm';
            button.type = 'button';
            button.textContent = 'Inspect';
            button.setAttribute('aria-label', `Inspect ${run.policy}, seed ${run.seed}`);
            button.addEventListener('click', () => void inspect(run));
            const download = document.createElement('a');
            download.href = base + encodeURIComponent(run.ledger);
            download.download = run.ledger;
            download.textContent = 'JSONL';
            download.setAttribute('aria-label', `Download ${run.policy}, seed ${run.seed}`);
            td.append(button, document.createTextNode(' '), download);
            rows.append(tr);
        });
    }
    seedSelect.addEventListener('change', render);
    document.getElementById('experiment-csv').addEventListener('click', () => {
        const csv = ['policy,seed,rare_hits,rare_recall,min_ratio,median_candidate,elapsed_s',
            ...visibleRuns().map(run => [run.policy, run.seed, run.rare_hits, run.rare_recall,
                run.min_ratio, run.median_candidate, run.elapsed_s].join(','))].join('\n');
        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = 'proofx-gb-001-summary.csv';
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    void (async () => {
        try {
            const response = await fetch(base + 'manifest.json');
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            manifest = await response.json();
            if (manifest.schema_version !== 'proofx.goldbach_benchmark.v1' || !manifest.runs.length ||
                manifest.config.max_n !== 10000 || manifest.config.budget !== 64 ||
                manifest.config.seeds.join(',') !== '0,1,2')
                throw new Error('Unexpected experiment');
            status.textContent = `${manifest.reference_size.toLocaleString()} reference candidates · ${manifest.rare_set_size} in the low-ratio set · ${manifest.runs.length} runs. Download the bundle and run the verifier to check these results.`;
            manifest.config.seeds.forEach(seed => seedSelect.add(new Option(String(seed), String(seed))));
            document.getElementById('experiment-provenance').textContent = JSON.stringify(manifest.provenance, null, 2);
            render();
            document.getElementById('experiment-table').hidden = false;
            document.getElementById('experiment-controls').hidden = false;
        }
        catch {
            status.textContent = 'The published results could not be loaded. Use the manifest or complete-bundle download above; no substitute values are displayed.';
        }
    })();
})();
