(() => {
  type Jsonish = string | number | boolean | null;
  type JsonValue = Jsonish | JsonValue[] | JsonMap;
  interface JsonMap {
    [key: string]: JsonValue | undefined;
  }

  type LedgerEntry = {
    candidate: number;
    conjecture: string;
    strategy: string;
    near_miss_score: number;
    timestamp: number | null;
    rng_seed: string;
    features: Record<string, Jsonish>;
    details: Record<string, Jsonish>;
    source: string;
    feature_count: number;
  };

  const allEntries: LedgerEntry[] = [];
  let sortCol: keyof LedgerEntry = "near_miss_score";
  let sortDir = -1;
  let expandedRow: HTMLTableRowElement | null = null;
  let loadedSource = "No source loaded";

  const loadBtn = byId<HTMLButtonElement>("load-btn");
  const sampleBtn = byId<HTMLButtonElement>("sample-btn");
  const fileInput = byId<HTMLInputElement>("file-input");
  const dropZone = byId<HTMLDivElement>("drop-zone");
  const tableContainer = byId<HTMLDivElement>("table-container");
  const visualPanel = byId<HTMLElement>("visual-panel");
  const summaryPanel = byId<HTMLElement>("summary-panel");
  const filterConjecture = byId<HTMLSelectElement>("filter-conjecture");
  const filterStrategy = byId<HTMLSelectElement>("filter-strategy");
  const candidateSearch = byId<HTMLInputElement>("candidate-search");
  const topKSelect = byId<HTMLSelectElement>("top-k");
  const minScore = byId<HTMLInputElement>("min-score");
  const minScoreValue = byId<HTMLSpanElement>("min-score-val");
  const featureSelect = byId<HTMLSelectElement>("feature-select");
  const exportBtn = byId<HTMLButtonElement>("export-btn");

  loadBtn.addEventListener("click", () => fileInput.click());
  sampleBtn.addEventListener("click", () => void loadSample());
  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (file) {
      void loadFile(file);
    }
  });

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = event.dataTransfer?.files[0];
    if (file) {
      void loadFile(file);
    }
  });

  [filterConjecture, filterStrategy, topKSelect, candidateSearch].forEach((control) => {
    control.addEventListener("input", render);
  });

  minScore.addEventListener("input", () => {
    minScoreValue.textContent = Number(minScore.value).toFixed(2);
    render();
  });

  featureSelect.addEventListener("change", renderFeatureBars);
  exportBtn.addEventListener("click", exportCsv);

  document.querySelectorAll<HTMLTableCellElement>("thead th[data-col]").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (!col || col === "rank") {
        return;
      }
      const nextCol = col as keyof LedgerEntry;
      sortDir = sortCol === nextCol ? sortDir * -1 : -1;
      sortCol = nextCol;
      document.querySelectorAll("thead th").forEach((header) => {
        header.classList.remove("sort-asc", "sort-desc");
      });
      th.classList.add(sortDir === -1 ? "sort-desc" : "sort-asc");
      render();
    });
  });

  void loadSample();

  async function loadSample(): Promise<void> {
    try {
      setDropMessage("Loading sample run...");
      const response = await fetch("/results.json", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = (await response.json()) as unknown;
      setEntries(normalizePayload(payload, "sample"), "Bundled sample run");
    } catch {
      setDropMessage("Drop a .jsonl ledger file here, or click to browse");
    }
  }

  async function loadFile(file: File): Promise<void> {
    const text = await file.text();
    const entries = parseLedgerText(text, file.name);
    if (entries.length === 0) {
      setDropMessage("No valid ledger entries found.");
      return;
    }
    setEntries(entries, file.name);
  }

  function setEntries(entries: LedgerEntry[], source: string): void {
    allEntries.splice(0, allEntries.length, ...entries);
    loadedSource = source;
    refreshStrategyFilter();
    refreshFeatureSelect();
    dropZone.hidden = true;
    tableContainer.hidden = false;
    visualPanel.hidden = false;
    summaryPanel.hidden = false;
    render();
  }

  function parseLedgerText(text: string, source: string): LedgerEntry[] {
    const trimmed = text.trim();
    if (!trimmed) {
      return [];
    }

    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        return normalizePayload(JSON.parse(trimmed) as unknown, source);
      } catch {
        return [];
      }
    }

    const entries: LedgerEntry[] = [];
    for (const line of trimmed.split(/\r?\n/)) {
      if (!line.trim()) {
        continue;
      }
      try {
        const normalized = normalizeEntry(JSON.parse(line) as JsonMap, source);
        if (normalized) {
          entries.push(normalized);
        }
      } catch {
        // Ignore malformed rows so one bad line does not discard a full run.
      }
    }
    return entries;
  }

  function normalizePayload(payload: unknown, source: string): LedgerEntry[] {
    if (Array.isArray(payload)) {
      return payload.flatMap((item) => normalizeEntry(item as JsonMap, source) ?? []);
    }
    if (!isMap(payload)) {
      return [];
    }

    const grouped: Array<[string, unknown]> = [
      ["collatz", payload.top_collatz],
      ["goldbach", payload.top_goldbach],
      ["riemann", payload.top_riemann],
    ];
    const groupedEntries = grouped.flatMap(([conjecture, rows]) => {
      return Array.isArray(rows)
        ? rows.flatMap((row) => normalizeEntry(row as JsonMap, source, conjecture) ?? [])
        : [];
    });

    const arrayEntries = ["entries", "ledger", "records"].flatMap((key) => {
      const rows = payload[key];
      return Array.isArray(rows)
        ? rows.flatMap((row) => normalizeEntry(row as JsonMap, source) ?? [])
        : [];
    });

    const single = normalizeEntry(payload, source);
    return groupedEntries.length > 0 || arrayEntries.length > 0
      ? [...groupedEntries, ...arrayEntries]
      : single
        ? [single]
        : [];
  }

  function normalizeEntry(raw: JsonMap, source: string, fallbackConjecture = "unknown"): LedgerEntry | null {
    if (!isMap(raw)) {
      return null;
    }
    const candidate = toNumber(raw.candidate);
    const nearMiss = toNumber(raw.near_miss_score ?? raw.score ?? 0);
    if (!Number.isFinite(candidate) || !Number.isFinite(nearMiss)) {
      return null;
    }

    const features = compactFlatMap(raw.features);
    const details = compactFlatMap(raw.details);
    const conjecture = String(raw.conjecture ?? fallbackConjecture).toLowerCase();
    const strategy = String(raw.strategy ?? "unknown");

    return {
      candidate,
      conjecture,
      strategy,
      near_miss_score: clamp01(nearMiss),
      timestamp: Number.isFinite(toNumber(raw.timestamp)) ? toNumber(raw.timestamp) : null,
      rng_seed: String(raw.rng_seed ?? raw.seed ?? ""),
      features,
      details,
      source,
      feature_count: Object.keys(features).length,
    };
  }

  function getFiltered(): LedgerEntry[] {
    const conjecture = filterConjecture.value;
    const strategy = filterStrategy.value;
    const min = Number(minScore.value);
    const search = candidateSearch.value.trim().toLowerCase();

    return allEntries.filter((entry) => {
      const candidateHit = search === "" || String(entry.candidate).includes(search);
      return (
        candidateHit &&
        (conjecture === "all" || entry.conjecture === conjecture) &&
        (strategy === "all" || entry.strategy === strategy) &&
        entry.near_miss_score >= min
      );
    });
  }

  function render(): void {
    const filtered = getFiltered();
    const topK = Number(topKSelect.value);
    const sorted = filtered.slice().sort(compareBySort);
    const visible = topK === 0 ? sorted : sorted.slice(0, topK);

    updateStats(filtered, visible);
    renderRows(visible);
    renderHistogram(filtered);
    renderCandidateMap(visible);
    renderFeatureBars();
  }

  function compareBySort(a: LedgerEntry, b: LedgerEntry): number {
    const av = a[sortCol];
    const bv = b[sortCol];
    if (typeof av === "string" || typeof bv === "string") {
      return sortDir * String(av).localeCompare(String(bv));
    }
    return sortDir * (Number(bv ?? 0) - Number(av ?? 0));
  }

  function updateStats(filtered: LedgerEntry[], visible: LedgerEntry[]): void {
    const counts = countBy(allEntries, (entry) => entry.conjecture);
    const strategies = new Set(allEntries.map((entry) => entry.strategy)).size;
    const max = Math.max(0, ...allEntries.map((entry) => entry.near_miss_score));
    const avg =
      allEntries.length === 0
        ? 0
        : allEntries.reduce((sum, entry) => sum + entry.near_miss_score, 0) / allEntries.length;

    byId("stat-total").textContent = allEntries.length.toLocaleString();
    byId("stat-source").textContent = loadedSource;
    byId("stat-showing").textContent = visible.length.toLocaleString();
    byId("stat-filtered").textContent = `${filtered.length.toLocaleString()} after filters`;
    byId("stat-max").textContent = max.toFixed(4);
    byId("stat-avg").textContent = `avg ${avg.toFixed(4)}`;
    byId("stat-mix").textContent = [
      `C ${counts.collatz ?? 0}`,
      `G ${counts.goldbach ?? 0}`,
      `R ${counts.riemann ?? 0}`,
    ].join(" / ");
    byId("stat-strategies").textContent = `${strategies} strategies`;
  }

  function renderRows(entries: LedgerEntry[]): void {
    const tbody = byId<HTMLTableSectionElement>("ledger-body");
    tbody.innerHTML = "";
    expandedRow = null;

    byId("empty-msg").hidden = entries.length > 0;
    if (entries.length === 0) {
      return;
    }

    entries.forEach((entry, index) => {
      const tr = document.createElement("tr");
      tr.innerHTML = [
        `<td class="ledger-rank">${index + 1}</td>`,
        `<td><b>${formatInteger(entry.candidate)}</b></td>`,
        `<td>${conjecturePill(entry.conjecture)}</td>`,
        `<td>${scoreBar(entry.near_miss_score)}</td>`,
        `<td class="ledger-muted-cell">${escapeHtml(entry.strategy)}</td>`,
        `<td class="ledger-muted-cell">${entry.feature_count}</td>`,
        `<td class="ledger-muted-cell">${formatTime(entry.timestamp)}</td>`,
      ].join("");
      tr.addEventListener("click", () => toggleDetail(tr, entry));
      tbody.appendChild(tr);
    });
  }

  function toggleDetail(tr: HTMLTableRowElement, entry: LedgerEntry): void {
    if (expandedRow && expandedRow !== tr) {
      expandedRow.classList.remove("expanded");
      const old = expandedRow.nextSibling;
      if (old instanceof HTMLElement && old.classList.contains("detail-row")) {
        old.remove();
      }
    }

    if (tr.classList.contains("expanded")) {
      tr.classList.remove("expanded");
      const next = tr.nextSibling;
      if (next instanceof HTMLElement && next.classList.contains("detail-row")) {
        next.remove();
      }
      expandedRow = null;
      return;
    }

    tr.classList.add("expanded");
    expandedRow = tr;

    const detail = document.createElement("tr");
    detail.className = "detail-row";
    const td = document.createElement("td");
    td.colSpan = 7;
    td.appendChild(buildDetail(entry));
    detail.appendChild(td);
    tr.insertAdjacentElement("afterend", detail);
  }

  function buildDetail(entry: LedgerEntry): HTMLElement {
    const panel = document.createElement("div");
    panel.className = "ledger-detail-panel";

    const featureItems = Object.entries(entry.features)
      .slice(0, 36)
      .map(([key, value]) => {
        return `<div class="ledger-feature-item"><div class="key">${labelize(key)}</div><div class="val">${escapeHtml(formatValue(value))}</div></div>`;
      })
      .join("");

    const detailItems = Object.entries(entry.details)
      .map(([key, value]) => `<span><span>${labelize(key)}</span> <b>${escapeHtml(formatValue(value))}</b></span>`)
      .join("");

    panel.innerHTML = [
      "<h3>Feature vector</h3>",
      `<div class="ledger-feature-grid">${featureItems || '<span class="muted">none</span>'}</div>`,
      "<h3>Diagnostics</h3>",
      `<div class="ledger-details-kv">${detailItems || '<span class="muted">none</span>'}</div>`,
      `<div class="ledger-seed-line">RNG seed: <b>${escapeHtml(entry.rng_seed || "not recorded")}</b> | Strategy: <b>${escapeHtml(entry.strategy)}</b></div>`,
    ].join("");

    const raw = document.createElement("pre");
    raw.className = "ledger-raw";
    raw.textContent = JSON.stringify(
      {
        candidate: entry.candidate,
        conjecture: entry.conjecture,
        near_miss_score: entry.near_miss_score,
        features: entry.features,
        details: entry.details,
      },
      null,
      2,
    );
    panel.appendChild(raw);
    return panel;
  }

  function renderHistogram(entries: LedgerEntry[]): void {
    const bins = Array.from({ length: 10 }, () => 0);
    for (const entry of entries) {
      bins[Math.min(9, Math.floor(entry.near_miss_score * 10))] += 1;
    }
    const max = Math.max(1, ...bins);
    const bars = bins
      .map((count, index) => {
        const x = 26 + index * 58;
        const height = Math.round((count / max) * 128);
        const y = 150 - height;
        return [
          `<rect x="${x}" y="${y}" width="38" height="${height}" rx="4" class="ledger-chart-bar"></rect>`,
          `<text x="${x + 19}" y="176" text-anchor="middle">${(index / 10).toFixed(1)}</text>`,
          `<text x="${x + 19}" y="${Math.max(18, y - 8)}" text-anchor="middle">${count}</text>`,
        ].join("");
      })
      .join("");

    byId("score-histogram").innerHTML = svgWrap(
      `${bars}<text x="26" y="205">score bucket lower bound</text>`,
      "0 0 640 220",
    );
  }

  function renderCandidateMap(entries: LedgerEntry[]): void {
    const visible = entries.slice(0, 140);
    if (visible.length === 0) {
      byId("candidate-map").innerHTML = emptyChart("No candidates");
      return;
    }

    const points = visible
      .map((entry, index) => {
        const x = 28 + (index / Math.max(1, visible.length - 1)) * 560;
        const y = 154 - entry.near_miss_score * 128;
        const colorClass = entry.conjecture === "goldbach" ? "goldbach" : entry.conjecture === "riemann" ? "riemann" : "collatz";
        return `<circle class="ledger-map-dot ${colorClass}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4"><title>${entry.conjecture} ${entry.candidate}: ${entry.near_miss_score.toFixed(4)}</title></circle>`;
      })
      .join("");

    byId("candidate-map").innerHTML = svgWrap(
      [
        '<line x1="28" y1="154" x2="592" y2="154" class="ledger-axis"></line>',
        '<line x1="28" y1="26" x2="28" y2="154" class="ledger-axis"></line>',
        points,
        '<text x="28" y="20">1.0</text>',
        '<text x="28" y="174">ranked entries</text>',
      ].join(""),
      "0 0 640 220",
    );
  }

  function renderFeatureBars(): void {
    const key = featureSelect.value;
    const rows = getFiltered()
      .map((entry) => ({ entry, value: key === "near_miss_score" ? entry.near_miss_score : toNumber(entry.features[key]) }))
      .filter((row) => Number.isFinite(row.value))
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);

    const max = Math.max(1, ...rows.map((row) => row.value));
    byId("feature-bars").innerHTML =
      rows
        .map(({ entry, value }) => {
          const width = Math.max(2, (value / max) * 100);
          return [
            '<div class="ledger-feature-bar">',
            `<span>${escapeHtml(entry.conjecture)} #${formatInteger(entry.candidate)}</span>`,
            '<div class="ledger-feature-bar__track">',
            `<i style="width:${width.toFixed(2)}%"></i>`,
            "</div>",
            `<b>${formatNumber(value)}</b>`,
            "</div>",
          ].join("");
        })
        .join("") || '<p class="empty-msg">No numeric values for this feature.</p>';
  }

  function refreshStrategyFilter(): void {
    const strategies = Array.from(new Set(allEntries.map((entry) => entry.strategy))).sort();
    filterStrategy.innerHTML = '<option value="all">All</option>';
    for (const strategy of strategies) {
      const option = document.createElement("option");
      option.value = strategy;
      option.textContent = strategy;
      filterStrategy.appendChild(option);
    }
  }

  function refreshFeatureSelect(): void {
    const keys = new Set<string>(["near_miss_score"]);
    for (const entry of allEntries) {
      Object.entries(entry.features).forEach(([key, value]) => {
        if (Number.isFinite(toNumber(value))) {
          keys.add(key);
        }
      });
    }
    featureSelect.innerHTML = "";
    Array.from(keys)
      .sort((a, b) => (a === "near_miss_score" ? -1 : b === "near_miss_score" ? 1 : a.localeCompare(b)))
      .forEach((key) => {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = key;
        featureSelect.appendChild(option);
      });
  }

  function exportCsv(): void {
    const rows = [["candidate", "conjecture", "near_miss_score", "strategy", "timestamp", "rng_seed"]];
    for (const entry of getFiltered()) {
      rows.push([
        String(entry.candidate),
        entry.conjecture,
        String(entry.near_miss_score),
        entry.strategy,
        String(entry.timestamp ?? ""),
        entry.rng_seed,
      ]);
    }
    const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
    a.download = "proofx_ledger.csv";
    a.click();
  }

  function setDropMessage(message: string): void {
    const first = dropZone.querySelector("p");
    if (first) {
      first.textContent = message;
    }
  }

  function scoreBar(score: number): string {
    const color = score >= 0.75 ? "var(--ledger-score-high)" : score >= 0.4 ? "var(--ledger-score-mid)" : "var(--ledger-score-low)";
    return [
      '<div class="ledger-score-bar">',
      `<span class="ledger-score-num" style="color:${color}">${score.toFixed(4)}</span>`,
      '<span class="ledger-score-track">',
      `<span class="ledger-score-fill" style="width:${(score * 100).toFixed(1)}%;background:${color}"></span>`,
      "</span></div>",
    ].join("");
  }

  function conjecturePill(conjecture: string): string {
    return `<span class="ledger-pill ledger-pill--${escapeHtml(conjecture)}">${escapeHtml(conjecture)}</span>`;
  }

  function svgWrap(content: string, viewBox: string): string {
    return `<svg viewBox="${viewBox}" role="img" preserveAspectRatio="none">${content}</svg>`;
  }

  function emptyChart(label: string): string {
    return svgWrap(`<text x="32" y="110">${escapeHtml(label)}</text>`, "0 0 640 220");
  }

  function compactFlatMap(value: unknown): Record<string, Jsonish> {
    if (!isMap(value)) {
      return {};
    }
    const out: Record<string, Jsonish> = {};
    Object.entries(value).forEach(([key, item]) => {
      if (typeof item === "string" || typeof item === "number" || typeof item === "boolean" || item === null) {
        out[key] = item;
      }
    });
    return out;
  }

  function countBy<T>(items: T[], keyFn: (item: T) => string): Record<string, number> {
    return items.reduce<Record<string, number>>((acc, item) => {
      const key = keyFn(item);
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
  }

  function isMap(value: unknown): value is JsonMap {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  function toNumber(value: unknown): number {
    return typeof value === "number" ? value : Number(value);
  }

  function clamp01(value: number): number {
    return Math.max(0, Math.min(1, value));
  }

  function formatInteger(value: number): string {
    return Math.round(value).toLocaleString();
  }

  function formatNumber(value: number): string {
    return Math.abs(value) >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : value.toFixed(4);
  }

  function formatValue(value: Jsonish): string {
    return typeof value === "number" ? formatNumber(value) : String(value);
  }

  function formatTime(timestamp: number | null): string {
    return timestamp ? new Date(timestamp * 1000).toLocaleString() : "-";
  }

  function labelize(value: string): string {
    return escapeHtml(value.replace(/_/g, " "));
  }

  function csvCell(value: string): string {
    return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
  }

  function escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => {
      const entities: Record<string, string> = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[char] ?? char;
    });
  }

  function byId<T extends HTMLElement = HTMLElement>(id: string): T {
    const element = document.getElementById(id);
    if (!element) {
      throw new Error(`Missing element #${id}`);
    }
    return element as T;
  }
})();
