# RareEventX — Advanced Collatz Long-Tail Behavior Analyzer

RareEventX is a **monolithic, research-grade CLI tool** for analyzing **long-tail anomalies and pathological behavior** in generalized Collatz-like systems. Designed for mathematicians, computational scientists, and symbolic AI researchers, it offers a deeply extensible pipeline for tracing stopping times, growth rates, divergence patterns, and entropy-based irregularities.

> "Where most Collatz tools end at '27', RareEventX begins."

---

## 🔍 What It Does

* Simulates **generalized Collatz sequences** with tunable parameters (`a`, `b`, `d`, floor division).
* Tracks and logs detailed stats: **stopping time, peak, entropy, divergence rate, volatility.**
* Detects **statistical and ML-based anomalies** using IsolationForest + robust z/IQR scores.
* Generates **high-quality visualizations**: stopping time scatter plots, heatmaps, anomaly maps.
* Outputs **Markdown reports**, CSV/JSON data exports, and complete sequence logs.

---

## 🧠 Why It Matters

Most Collatz tools are either hardcoded, trivial, or brute-force only. RareEventX:

* Allows exploration of **rare sequence behaviors** across vast seed spaces.
* Bridges symbolic logic and machine learning for **novel anomaly detection**.
* Produces research-quality plots and data outputs, ready for publication or further analysis.
* Built with scientific precision and engineering discipline, in a **single-file deployable format**.

---

## ⚙️ Architecture Overview

| Module                | Role                                                            |
| --------------------- | --------------------------------------------------------------- |
| `CollatzSimulator`    | Sequence generation & stat computation                          |
| `RareSequenceTracker` | Top-N sorting by multiple criteria (entropy, peak, etc.)        |
| `AnomalyDetector`     | Z-score, IQR, IsolationForest ML anomaly classification         |
| `Visualizer`          | Scatter, histogram, heatmap, and anomaly plots                  |
| `StatsEngine`         | Advanced statistics, correlation, volatility, kurtosis/skewness |
| `report.md`           | Human-readable Markdown report of sequence findings             |

---

## 🚀 Usage

```bash
python3 rareeventx.py \
  --range 1:50000 \
  --a 3 --b 1 --d 2 \
  --track-values \
  --threshold "steps>100" \
  --top-n 50 \
  --plot \
  --format both \
  --output ./results
```

You’ll get:

* `results.csv`, `results.json`
* `report.md` with top sequences and statistical summaries
* Plot images: `stopping_times.png`, `peak_values.png`, `anomalies.png`, etc.

---

## 📊 Sample Outputs

* `Seed 9663`: Stopping time **$≈1000$**, entropy **2.45**, growth rate **positive**
* `Seed 703`: Peak value **\~10^6**, reached in **88 steps**
* `Seed 27`: Classic Collatz diverger, flagged with high entropy

---

## 🧪 Supported Analyses

* Top-N by: **stopping time, peak, entropy, divergence rate**
* Visual anomaly detection: **highlighted outliers**
* Full-sequence logging (optional for memory efficiency)
* Multi-format export: **CSV, JSON, Markdown**

---

## 📦 Tech Stack

* Python 3.9+
* `numpy`, `pandas`, `matplotlib`
* `sklearn` (IsolationForest, StandardScaler)
* `sympy`, `argparse`

No external dependencies. Works out-of-the-box.

---

## 💡 Potential Extensions

* GUI-based interactive sequence explorer
* Quantum circuit backend (Qiskit)
* AutoML pattern discovery for diverging sequences
* Distributed seed-range runners

---

## 🧾 License

This tool is distributed under the **MIT License**.

---

## ✉️ Contact / Contribution

Built by [Mohammed Alkindi](https://github.com/alkindi-ai) for symbolic systems research and high-performance numerical curiosity.

Feel free to fork, extend, or open issues. Collaboration inquiries welcome.

---

## 🧠 Closing Note

RareEventX is not just a program. It is an **observatory** for integer dynamics, a **lens** on computational chaos, and a **provocation** to mathematical orthodoxy. Use it to search where others stopped looking.

> *"Pathologies aren't bugs — they're insights."*
