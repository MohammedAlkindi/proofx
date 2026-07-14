"use strict";
(() => {
    const PRIME_COUNT_LIMIT = 500000;
    const input = byId("riemann-input");
    const button = byId("riemann-run");
    const metrics = byId("riemann-metrics");
    const chart = byId("riemann-prime-chart");
    const output = byId("riemann-result");
    button.addEventListener("click", run);
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            run();
        }
    });
    run();
    function millerRabin(n) {
        if (n < 2)
            return false;
        if ([2, 3, 5, 7, 11, 13].includes(n))
            return true;
        if (n % 2 === 0 || n % 3 === 0)
            return false;
        let d = n - 1;
        let r = 0;
        while (d % 2 === 0) {
            d = Math.floor(d / 2);
            r += 1;
        }
        for (const a of [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]) {
            if (a >= n)
                continue;
            let x = modpow(a, d, n);
            if (x === 1 || x === n - 1)
                continue;
            let witnessPassed = false;
            for (let i = 0; i < r - 1; i += 1) {
                x = (x * x) % n;
                if (x === n - 1) {
                    witnessPassed = true;
                    break;
                }
            }
            if (!witnessPassed)
                return false;
        }
        return true;
    }
    function modpow(base, exp, mod) {
        let result = 1;
        let current = base % mod;
        let power = exp;
        while (power > 0) {
            if (power % 2 === 1)
                result = (result * current) % mod;
            power = Math.floor(power / 2);
            current = (current * current) % mod;
        }
        return result;
    }
    function nearestPrimes(n) {
        let prev = null;
        let next = null;
        for (let candidate = n - 1; candidate >= 2; candidate -= 1) {
            if (millerRabin(candidate)) {
                prev = candidate;
                break;
            }
        }
        for (let candidate = n + 1; candidate <= n + 10000; candidate += 1) {
            if (millerRabin(candidate)) {
                next = candidate;
                break;
            }
        }
        return { prev, next };
    }
    function primePrefix(limit) {
        const sieve = new Uint8Array(limit + 1).fill(1);
        sieve[0] = 0;
        sieve[1] = 0;
        for (let i = 2; i * i <= limit; i += 1) {
            if (sieve[i]) {
                for (let j = i * i; j <= limit; j += i) {
                    sieve[j] = 0;
                }
            }
        }
        const prefix = new Uint32Array(limit + 1);
        let count = 0;
        for (let i = 0; i <= limit; i += 1) {
            if (sieve[i])
                count += 1;
            prefix[i] = count;
        }
        return prefix;
    }
    function primeCountSeries(n) {
        const limit = Math.min(n, PRIME_COUNT_LIMIT);
        if (limit < 2) {
            return { limit, count: 0, exact: [], approx: [] };
        }
        const prefix = primePrefix(limit);
        const sampleCount = Math.min(18, Math.max(3, limit - 1));
        const seen = new Set();
        const exact = [];
        const approx = [];
        for (let i = 0; i < sampleCount; i += 1) {
            const x = Math.round(2 + ((limit - 2) * i) / (sampleCount - 1));
            if (seen.has(x))
                continue;
            seen.add(x);
            exact.push({ x, y: prefix[x] });
            approx.push({ x, y: x / Math.log(x) });
        }
        return { limit, count: prefix[limit], exact, approx };
    }
    function run() {
        const n = Number.parseInt(input.value, 10);
        if (!Number.isFinite(n) || n < 2 || n > 10000000) {
            renderMessage("Enter an integer from 2 to 10,000,000.");
            return;
        }
        const isPrime = millerRabin(n);
        const near = nearestPrimes(n);
        const approxAtN = n / Math.log(n);
        const series = primeCountSeries(n);
        renderMetrics(n, isPrime, series, approxAtN);
        renderPrimeChart(n, series);
        renderPreview(n, isPrime, near, series, approxAtN);
    }
    function renderMetrics(n, isPrime, series, approxAtN) {
        metrics.innerHTML = [
            metricCard("Input", n.toLocaleString(), "candidate"),
            metricCard("Prime", isPrime ? "yes" : "no", "deterministic witnesses in demo range"),
            metricCard(series.limit === n ? "pi(n)" : "pi(cap)", series.count.toLocaleString(), `through ${series.limit.toLocaleString()}`),
            metricCard("n / log(n)", Math.round(approxAtN).toLocaleString(), "simple approximation"),
        ].join("");
    }
    function renderPrimeChart(n, series) {
        if (!series.exact.length) {
            chart.innerHTML = '<div class="engine-chart-empty">No prime-count samples to display.</div>';
            return;
        }
        const width = 720;
        const height = 270;
        const pad = 40;
        const yMax = Math.max(1, ...series.exact.map((point) => point.y), ...series.approx.map((point) => point.y));
        const xMax = Math.max(2, series.limit);
        const toX = (x) => pad + ((x - 2) / Math.max(1, xMax - 2)) * (width - pad * 2);
        const toY = (y) => height - pad - (y / yMax) * (height - pad * 2);
        const exactPath = linePath(series.exact, toX, toY);
        const approxPath = linePath(series.approx, toX, toY);
        chart.innerHTML = [
            `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Prime-count comparison through ${series.limit.toLocaleString()}" preserveAspectRatio="none">`,
            `<line class="engine-axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>`,
            `<line class="engine-axis" x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}"></line>`,
            `<path class="engine-line" d="${exactPath}"><title>exact pi(x)</title></path>`,
            `<path class="engine-line engine-line--secondary" d="${approxPath}"><title>x / log(x)</title></path>`,
            `<text x="${pad}" y="18">count</text>`,
            `<text x="${width - pad}" y="${height - 8}" text-anchor="end">${series.limit.toLocaleString()}</text>`,
            `<g class="engine-legend"><circle cx="${width - 170}" cy="18" r="4"></circle><text x="${width - 160}" y="22">exact pi(x)</text><circle class="secondary" cx="${width - 82}" cy="18" r="4"></circle><text x="${width - 72}" y="22">x / log(x)</text></g>`,
            "</svg>",
        ].join("");
    }
    function linePath(points, toX, toY) {
        return points
            .map((point, index) => `${index === 0 ? "M" : "L"} ${toX(point.x).toFixed(2)} ${toY(point.y).toFixed(2)}`)
            .join(" ");
    }
    function renderPreview(n, isPrime, near, series, approxAtN) {
        const nearest = isPrime
            ? `${n.toLocaleString()} (itself)`
            : `${near.prev ? `${near.prev.toLocaleString()} below` : "none found below"} / ${near.next ? `${near.next.toLocaleString()} above` : "none found above within search cap"}`;
        output.textContent = [
            `n              : ${n.toLocaleString()}`,
            `Is prime       : ${isPrime ? "yes" : "no"}`,
            `Nearest prime  : ${nearest}`,
            `pi(n) exact    : ${n <= PRIME_COUNT_LIMIT ? series.count.toLocaleString() : `capped at ${series.count.toLocaleString()} primes through 500,000`}`,
            `n / log(n)     : about ${Math.round(approxAtN).toLocaleString()}`,
        ].join("\n");
    }
    function renderMessage(message) {
        metrics.innerHTML = "";
        chart.innerHTML = "";
        output.textContent = message;
    }
    function metricCard(label, value, note) {
        return [
            '<article class="engine-metric">',
            `<span>${escapeHtml(label)}</span>`,
            `<b>${escapeHtml(value)}</b>`,
            `<small>${escapeHtml(note)}</small>`,
            "</article>",
        ].join("");
    }
    function escapeHtml(value) {
        return value.replace(/[&<>"']/g, (char) => {
            const entities = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            };
            return entities[char] ?? char;
        });
    }
    function byId(id) {
        const element = document.getElementById(id);
        if (!element) {
            throw new Error(`Missing element #${id}`);
        }
        return element;
    }
})();
