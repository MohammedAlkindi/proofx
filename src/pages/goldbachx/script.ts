(() => {
  type Pair = [number, number];

  const input = byId<HTMLInputElement>("goldbach-input");
  const button = byId<HTMLButtonElement>("goldbach-run");
  const metrics = byId<HTMLDivElement>("goldbach-metrics");
  const pairChart = byId<HTMLDivElement>("goldbach-pairs-chart");
  const neighborhoodChart = byId<HTMLDivElement>("goldbach-neighborhood-chart");
  const output = byId<HTMLPreElement>("goldbach-result");

  button.addEventListener("click", run);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      run();
    }
  });

  run();

  function sieve(limit: number): Uint8Array {
    const isPrime = new Uint8Array(limit + 1).fill(1);
    isPrime[0] = 0;
    isPrime[1] = 0;
    for (let i = 2; i * i <= limit; i += 1) {
      if (isPrime[i]) {
        for (let j = i * i; j <= limit; j += i) {
          isPrime[j] = 0;
        }
      }
    }
    return isPrime;
  }

  function decompose(n: number, isPrime: Uint8Array): Pair[] {
    const pairs: Pair[] = [];
    for (let p = 2; p <= Math.floor(n / 2); p += 1) {
      if (isPrime[p] && isPrime[n - p]) {
        pairs.push([p, n - p]);
      }
    }
    return pairs;
  }

  function countPairs(n: number, isPrime: Uint8Array): number {
    let count = 0;
    for (let p = 2; p <= Math.floor(n / 2); p += 1) {
      if (isPrime[p] && isPrime[n - p]) {
        count += 1;
      }
    }
    return count;
  }

  function nearbyEvenInputs(n: number): number[] {
    let start = Math.max(4, n - 16);
    let end = Math.min(100_000, n + 16);
    if (start % 2 !== 0) start += 1;
    if (end % 2 !== 0) end -= 1;
    while (end - start < 32 && start > 4) start -= 2;
    while (end - start < 32 && end < 100_000) end += 2;

    const values: number[] = [];
    for (let value = start; value <= end; value += 2) {
      values.push(value);
    }
    return values;
  }

  function run(): void {
    const n = Number.parseInt(input.value, 10);
    if (!Number.isFinite(n) || n < 4 || n % 2 !== 0) {
      renderMessage("Enter an even integer >= 4.");
      return;
    }
    if (n > 100_000) {
      renderMessage("Enter a value <= 100,000 for in-browser computation.");
      return;
    }

    const nearby = nearbyEvenInputs(n);
    const isPrime = sieve(Math.max(n, nearby[nearby.length - 1] ?? n));
    const pairs = decompose(n, isPrime);
    renderMetrics(n, pairs);
    renderPairPositions(n, pairs);
    renderNeighborhood(n, nearby, isPrime);
    renderPreview(n, pairs);
  }

  function renderMetrics(n: number, pairs: Pair[]): void {
    const widestGap = pairs.reduce((maxGap, pair) => Math.max(maxGap, pair[1] - pair[0]), 0);
    metrics.innerHTML = [
      metricCard("Input", n.toLocaleString(), "even candidate"),
      metricCard("Partitions", pairs.length.toLocaleString(), "prime pairs"),
      metricCard("Smallest Pair", pairs[0] ? `${pairs[0][0]} + ${pairs[0][1]}` : "none", "first decomposition"),
      metricCard("Pair Density", (pairs.length / Math.max(1, Math.floor(n / 2))).toFixed(4), "pairs per p <= n / 2"),
      metricCard("Widest Gap", widestGap.toLocaleString(), "q - p"),
    ].join("");
  }

  function renderPairPositions(n: number, pairs: Pair[]): void {
    const width = 720;
    const height = 150;
    const pad = 36;
    const domainMax = Math.max(2, Math.floor(n / 2));

    if (!pairs.length) {
      pairChart.innerHTML = '<div class="engine-chart-empty">No prime-pair decompositions found.</div>';
      return;
    }

    const marks = pairs
      .map((pair) => {
        const x = pad + ((pair[0] - 2) / Math.max(1, domainMax - 2)) * (width - pad * 2);
        return `<line class="engine-rug" x1="${x.toFixed(2)}" x2="${x.toFixed(2)}" y1="26" y2="${height - pad}"><title>${pair[0].toLocaleString()} + ${pair[1].toLocaleString()}</title></line>`;
      })
      .join("");

    pairChart.innerHTML = [
      `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Prime-pair positions for ${n}" preserveAspectRatio="none">`,
      `<line class="engine-axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>`,
      marks,
      `<text x="${pad}" y="${height - 8}">2</text>`,
      `<text x="${width - pad}" y="${height - 8}" text-anchor="end">${domainMax.toLocaleString()}</text>`,
      "</svg>",
    ].join("");
  }

  function renderNeighborhood(n: number, nearby: number[], isPrime: Uint8Array): void {
    const bars = nearby.map((value) => ({ value, count: countPairs(value, isPrime) }));
    const maxCount = Math.max(1, ...bars.map((bar) => bar.count));
    const width = 720;
    const height = 250;
    const pad = 36;
    const plotWidth = width - pad * 2;
    const step = plotWidth / bars.length;
    const barWidth = Math.max(6, step * 0.62);

    const marks = bars
      .map((bar, index) => {
        const x = pad + index * step + (step - barWidth) / 2;
        const h = (bar.count / maxCount) * (height - pad * 2);
        const y = height - pad - h;
        const selected = bar.value === n ? " engine-bar--selected" : "";
        return `<rect class="engine-bar${selected}" x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${barWidth.toFixed(2)}" height="${Math.max(1, h).toFixed(2)}" rx="2"><title>${bar.value.toLocaleString()}: ${bar.count.toLocaleString()} pairs</title></rect>`;
      })
      .join("");

    const labels = bars
      .filter((_, index) => index % Math.max(1, Math.ceil(bars.length / 5)) === 0)
      .map((bar, index) => {
        const sourceIndex = bars.findIndex((candidate) => candidate.value === bar.value);
        const x = pad + sourceIndex * step + step / 2;
        return `<text x="${x.toFixed(2)}" y="${height - 8}" text-anchor="middle">${bar.value.toLocaleString()}</text>`;
      })
      .join("");

    neighborhoodChart.innerHTML = [
      `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Goldbach partition counts around ${n}" preserveAspectRatio="none">`,
      `<line class="engine-axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>`,
      `<line class="engine-axis" x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}"></line>`,
      marks,
      `<text x="${pad}" y="18">partition count</text>`,
      labels,
      "</svg>",
    ].join("");
  }

  function renderPreview(n: number, pairs: Pair[]): void {
    const lines = [`Input          : ${n.toLocaleString()}`, `Decompositions : ${pairs.length}`, ""];
    const visible = pairs.length <= 20 ? pairs : pairs.slice(0, 20);
    visible.forEach((pair, index) => {
      lines.push(`  ${index + 1}.  ${pair[0]} + ${pair[1]}`);
    });
    if (pairs.length > 20) {
      lines.push(`  ... and ${pairs.length - 20} more pairs`);
    }
    output.textContent = lines.join("\n");
  }

  function renderMessage(message: string): void {
    metrics.innerHTML = "";
    pairChart.innerHTML = "";
    neighborhoodChart.innerHTML = "";
    output.textContent = message;
  }

  function metricCard(label: string, value: string, note: string): string {
    return [
      '<article class="engine-metric">',
      `<span>${escapeHtml(label)}</span>`,
      `<b>${escapeHtml(value)}</b>`,
      `<small>${escapeHtml(note)}</small>`,
      "</article>",
    ].join("");
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

  function byId<T extends HTMLElement>(id: string): T {
    const element = document.getElementById(id);
    if (!element) {
      throw new Error(`Missing element #${id}`);
    }
    return element as T;
  }
})();
