# RHVT+ : Riemann Hypothesis Verification Toolkit Plus

## Overview

**RHVT+** is a production-grade, high-precision, high-performance computational toolkit designed for the rigorous exploration and verification of the Riemann Hypothesis. Engineered with extensibility, reproducibility, and interactivity in mind, RHVT+ enables researchers, mathematicians, and computational scientists to probe the non-trivial zeros of the Riemann zeta function at scale.

## Features

* **Multi-Backend Computation**: Auto-switching between CPU, GPU (CuPy/Numba), and distributed cluster backends (Dask/Ray)
* **Interactive Visualization**: Real-time dashboard powered by Streamlit with Plotly integration
* **Symbolic Verification**: Integration with SymPy and optional SageMath backends for symbolic proof checks
* **ML-Powered Analysis**: Includes anomaly detection on zero spacings using Isolation Forests or z-score thresholds
* **Distributed Processing**: Horizontal scalability through Dask or Ray with pluggable task workers
* **Automated Reporting**: Generate LaTeX reports with statistical summaries, provenance logs, and optional signing
* **Provenance Tracking**: Full configuration and execution trace logs with cryptographic hashing
* **Modular Plugin Architecture**: Dynamically load analysis modules, visualizations, and backends
* **Built-in Testing Suite**: `pytest`-based tests for full coverage of computational and analytical logic

## Architecture

```
[ CLI / Dashboard ]
       |
[ ConfigManager ]
       |
[ Core Engine ] ---- [ Backends: CPU / GPU / Cluster ]
       |
[ Analysis ] --- [ ML / Symbolic / Statistical ]
       |
[ Visualization ] --- [ Interactive / Static ]
       |
[ Reporting ] --- [ LaTeX + Provenance ]
       |
[ Plugin Manager ]
```

## Usage

### CLI Example:

```bash
$ python rhvt_plus.py --zeros 1e6 --precision 200 --gpu --dashboard
```

### Python Module Example:

```python
from rhvt_plus import ConfigManager, BackendManager

cfg = ConfigManager("my_config.yaml")
backend = BackendManager.get_backend("gpu", cfg)
zeros = backend.compute_zeros(1000)
stats = backend.verify_critical_line(zeros)
```

### Launch Dashboard:

```bash
$ python rhvt_plus.py --dashboard
```

## Configuration

All parameters can be set via `rhvt_config.yaml`, CLI, or dynamically during execution:

* `precision.digits`: Number of decimal digits to compute
* `computation.backend`: auto | cpu | gpu | cluster
* `verification.*`: Enables and tunes methods
* `visualization.dashboard.port`: Change port (default 8501)
* `reporting.format`: latex | html

## Installation

```bash
$ git clone https://github.com/yourname/rhvt_plus.git
$ cd rhvt_plus
$ pip install -r requirements.txt
```

Additional packages for full feature support:

```bash
$ pip install sympy sage dask[complete] ray scikit-learn streamlit plotly
```

## Plugins

Create Python files in the `plugins/` directory with a `register_plugin(config)` method. Example plugin template:

```python
def register_plugin(config):
    config.register_analysis("new_method", my_analysis_fn)
```

Enable in config:

```yaml
plugins:
  enabled: ["my_plugin"]
```

## Provenance & Signing

* SHA256 hash of full configuration is stored
* Timeline of all events (CLI changes, plugin loads, etc.)
* Optional signing for academic/secure environments

## License

MIT License. Feel free to fork, enhance, and cite.

## Citation

```bibtex
@software{rhvtplus2025,
  author = {Alkindi, Mohammed},
  title = {RHVT+ - Riemann Hypothesis Verification Toolkit Plus},
  year = {2025},
  howpublished = {\url{https://github.com/yourname/rhvt_plus}},
}
```

---

"Mathematics is not about numbers, equations, or algorithms: it is about understanding." – William Thurston
