# 📘 CollatzAnalyzer: Exponential Stopping Time Explorer

An advanced, production-grade analysis suite for exploring the **Collatz Conjecture** using exponential modeling, multiprocessing, and statistical visualization. Designed for deep mathematical insight, research scalability, and enterprise-grade result handling.

---

## 🚀 Features

- ⚡ **Multiprocessing-Powered Engine**: Parallelized computation of stopping times for `base^n` up to 1,000,000 iterations
- 📉 **Model Fitting**: Fits an exponential curve `T(n) = a * b^n + c` to analyze behavior patterns
- 📊 **High-Quality Visualizations**: Plots include:
  - Colored scatter & curve overlays
  - Residual diagnostics with statistical summary
  - 3D surface visualization (`n`, `log(value)`, `stopping time`)
  - Distribution histogram with KDE
  - Log-log trend analysis
- 📂 **Export Pipeline**: Saves:
  - CSV logs
  - Fitted model parameters
  - Plots (`.png` @ 300 DPI)
- 🧠 **Numerical Stability**: Handles overflows and max iteration caps gracefully
- 📈 **Advanced Plot Styling**: Seaborn + Matplotlib for clean modern outputs

---

## 🧱 Project Structure

```
collatz_analyzer/
├── collatz_analyzer.py        # Main executable module
├── collatz_results.log        # Stopping time logs
├── fitted_parameters.txt      # Exponential model parameters
├── *.png                      # Saved plots (main, residuals, distribution, 3D)
└── requirements.txt           # Dependencies list
```

---

## 🧪 Sample Usage

```bash
$ python collatz_analyzer.py

Collatz Conjecture Stoiting Time Analyzer
----------------------------------------
Enter base value (default 2): 2
Enter start exponent: 10
Enter end exponent: 40
```

Example Output:
```
n = 10, 2^10 = 1024, T = 39
n = 15, 2^15 = 32768, T = 52
...
Fitted: T(n) = 2.93 * 1.15^n + 6.47
```

---

## 📦 Installation

```bash
pip install -r requirements.txt
```

Required Libraries:
```text
numpy
matplotlib
scipy
pandas
seaborn
```

---

## 📈 Output Files

- `collatz_results.log`: CSV-style log with exponent, value, and stopping time
- `fitted_parameters.txt`: Fitted parameters `a`, `b`, `c` with standard errors
- `*.png`:
  - `collatz_main_plot.png`
  - `collatz_residuals.png`
  - `collatz_distribution.png`
  - `collatz_3d_plot.png`

---

## 📜 License

MIT License — Use freely with attribution. Ideal for research, education, or symbolic computing integrations.

© 2025 Mohammed Alkindi — CollatzLab
