"use strict";
(() => {
    const input = byId("collatz-input");
    const fuelInput = byId("collatz-fuel");
    const button = byId("collatz-run");
    const metrics = byId("collatz-metrics");
    const chart = byId("collatz-chart");
    const parity = byId("collatz-parity");
    const output = byId("collatz-result");
    button.addEventListener("click", run);
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            run();
        }
    });
    fuelInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            run();
        }
    });
    run();
    function trace(n, fuel) {
        const sequence = [n];
        let current = n;
        let maxValue = n;
        let steps = 0;
        let oddCount = n % 2 === 1 ? 1 : 0;
        let evenCount = n % 2 === 0 ? 1 : 0;
        let maxJump = 0;
        while (current !== 1 && steps < fuel) {
            const previous = current;
            current = current % 2 === 0 ? current / 2 : 3 * current + 1;
            sequence.push(current);
            maxValue = Math.max(maxValue, current);
            maxJump = Math.max(maxJump, Math.abs(current - previous));
            if (current % 2 === 0) {
                evenCount += 1;
            }
            else {
                oddCount += 1;
            }
            steps += 1;
        }
        return {
            sequence,
            steps,
            maxValue,
            converged: current === 1,
            oddCount,
            evenCount,
            maxJump,
        };
    }
    function run() {
        const n = Number.parseInt(input.value, 10);
        const fuel = Number.parseInt(fuelInput.value, 10);
        if (!Number.isFinite(n) || n < 1 || n > 10000000) {
            renderMessage("Enter an integer from 1 to 10,000,000.");
            return;
        }
        if (!Number.isFinite(fuel) || fuel < 100 || fuel > 100000) {
            renderMessage("Fuel must be between 100 and 100,000 steps.");
            return;
        }
        const result = trace(n, fuel);
        renderMetrics(n, result);
        renderChart(result);
        renderParity(result.sequence);
        renderPreview(n, result);
    }
    function renderMetrics(n, result) {
        const oddShare = result.oddCount / result.sequence.length;
        metrics.innerHTML = [
            metricCard("Start", n.toLocaleString(), "candidate"),
            metricCard("Stopping Time", `${result.steps}`, result.converged ? "reaches 1" : "fuel limit"),
            metricCard("Peak", result.maxValue.toLocaleString(), `${(result.maxValue / n).toFixed(2)}x start`),
            metricCard("Odd Share", `${(oddShare * 100).toFixed(1)}%`, `${result.oddCount} odd values`),
            metricCard("Largest Jump", result.maxJump.toLocaleString(), "single step"),
        ].join("");
    }
    function renderChart(result) {
        const values = result.sequence;
        const width = 720;
        const height = 260;
        const pad = 28;
        const maxLog = Math.max(1, ...values.map((value) => Math.log2(value)));
        const points = values
            .map((value, index) => {
            const x = pad + (index / Math.max(1, values.length - 1)) * (width - pad * 2);
            const y = height - pad - (Math.log2(value) / maxLog) * (height - pad * 2);
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
            .join(" ");
        const peakIndex = values.indexOf(result.maxValue);
        const peakX = pad + (peakIndex / Math.max(1, values.length - 1)) * (width - pad * 2);
        const peakY = height - pad - (Math.log2(result.maxValue) / maxLog) * (height - pad * 2);
        chart.innerHTML = [
            `<svg viewBox="0 0 ${width} ${height}" role="img" preserveAspectRatio="none">`,
            `<line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="collatz-axis"></line>`,
            `<line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="collatz-axis"></line>`,
            `<polyline class="collatz-line" points="${points}"></polyline>`,
            `<circle class="collatz-peak" cx="${peakX.toFixed(2)}" cy="${peakY.toFixed(2)}" r="5"><title>Peak ${result.maxValue}</title></circle>`,
            `<text x="${pad}" y="18">log2(value)</text>`,
            `<text x="${width - pad}" y="${height - 6}" text-anchor="end">step ${result.steps}</text>`,
            "</svg>",
        ].join("");
    }
    function renderParity(sequence) {
        const maxCells = 180;
        const stride = Math.max(1, Math.ceil(sequence.length / maxCells));
        const cells = sequence
            .filter((_, index) => index % stride === 0)
            .map((value) => `<span class="${value % 2 === 0 ? "even" : "odd"}" title="${value % 2 === 0 ? "even" : "odd"}"></span>`)
            .join("");
        parity.innerHTML = `<div class="collatz-parity__label">Parity strip</div><div class="collatz-parity__cells">${cells}</div>`;
    }
    function renderPreview(n, result) {
        const preview = result.sequence.length <= 28
            ? result.sequence.join(" -> ")
            : `${result.sequence.slice(0, 14).join(" -> ")} -> ... -> ${result.sequence.slice(-8).join(" -> ")}`;
        output.textContent = [
            `Starting value : ${n.toLocaleString()}`,
            `Stopping time  : ${result.steps} steps`,
            `Peak value     : ${result.maxValue.toLocaleString()}`,
            `Converged to 1 : ${result.converged ? "yes" : "fuel limit reached"}`,
            "",
            `Sequence (${result.sequence.length} values):`,
            preview,
        ].join("\n");
    }
    function renderMessage(message) {
        metrics.innerHTML = "";
        chart.innerHTML = "";
        parity.innerHTML = "";
        output.textContent = message;
    }
    function metricCard(label, value, note) {
        return [
            '<article class="collatz-metric">',
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
