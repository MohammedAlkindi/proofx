"""
Symbolic Decision Boundary Engine
=================================
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import sys
import time
import warnings
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, auto
from math import log
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import shap
from joblib import dump, load
from rich.console import Console
from rich.progress import track
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# --------------------------
# Configuration Constants
# --------------------------

MAX_CACHE_SIZE = 1_000_000  # Maximum cached trajectories (soft limit, by file count)
DEFAULT_MAX_ITER = 100_000  # Default maximum iterations
CHAOS_THRESHOLD = 1.0       # Lyapunov exponent threshold for chaos
CYCLE_DETECTION_WINDOW = 100  # Lookback window for cycle detection
COMPRESSION_LEVEL = 6         # Default gzip compression level

# --------------------------
# Core Data Structures
# --------------------------

class SystemBehavior(Enum):
    """Enhanced behavior classification with subcategories"""
    CONVERGES = auto()
    DIVERGES_POSITIVE = auto()
    DIVERGES_NEGATIVE = auto()
    CYCLIC_SHORT = auto()  # Cycles < 100 steps
    CYCLIC_LONG = auto()   # Cycles >= 100 steps
    CHAOTIC = auto()       # Positive Lyapunov exponent
    CYCLIC = auto()        # Back-compat umbrella; mapped to SHORT/LONG when possible
    UNKNOWN = auto()


@dataclass
class AttractorProperties:
    cycle_length: int = 0
    basin_size: int = 1
    stability: float = 0.0  # 0-1 scale of attractor stability
    is_chaotic: bool = False


@dataclass
class TrajectoryResult:
    seed: Union[int, float]
    rule_hash: str
    behavior: SystemBehavior
    stopping_time: Optional[int]
    max_value: float
    min_value: float
    parity_sequence: str
    entropy: float
    lyapunov_exponent: float
    trajectory: List[float] = field(repr=False)
    compressed_size: int = 0
    attractor: Optional[AttractorProperties] = None

    def __post_init__(self) -> None:
        # Post-processing for behavior classification and consistency
        if self.behavior == SystemBehavior.CONVERGES and abs(self.lyapunov_exponent) > CHAOS_THRESHOLD:
            self.behavior = SystemBehavior.CHAOTIC
        if self.behavior == SystemBehavior.CYCLIC and self.attractor:
            self.behavior = (
                SystemBehavior.CYCLIC_LONG if self.attractor.cycle_length >= 100 else SystemBehavior.CYCLIC_SHORT
            )


@dataclass
class RuleParameters:
    k: float
    b: float
    divisor: float
    modulus: Optional[int] = None
    max_iterations: int = DEFAULT_MAX_ITER
    escape_threshold: float = 1e20
    precision: int = 16  # Decimal precision for float comparisons

    def __post_init__(self) -> None:
        self.rule_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Create a unique cryptographic hash for the rule parameters"""
        components = (
            f"{self.k:.{self.precision}f}_"
            f"{self.b:.{self.precision}f}_"
            f"{self.divisor:.{self.precision}f}_"
            f"{self.modulus}"
        )
        return hashlib.sha256(components.encode()).hexdigest()


# --------------------------
# Core Engine
# --------------------------

class SymbolicBoundaryEngine:
    def __init__(self, cache_dir: str = "trajectory_cache", use_gpu: bool = False):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._init_ml_model()
        self.console = Console()
        self.use_gpu = use_gpu
        self._setup_warnings()
        # rule_hash → RuleParameters (for feature extraction / provenance)
        self.rule_index: Dict[str, RuleParameters] = {}

    # --- setup helpers ---
    def _setup_warnings(self) -> None:
        warnings.simplefilter("ignore", RuntimeWarning)
        np.seterr(all="ignore")

    def _init_ml_model(self) -> None:
        """Initialize the ML models with enhanced architecture"""
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )
        self.regressor = RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            random_state=42,
            n_jobs=-1,
        )
        self.models_trained = False
        self.label_encoder = LabelEncoder()

    # --- rule/trajectory mechanics ---
    def register_rule(self, params: RuleParameters) -> None:
        self.rule_index[params.rule_hash] = params

    def _load_rule_params(self, rule_hash: str) -> RuleParameters:
        rp = self.rule_index.get(rule_hash)
        if rp is None:
            # Fallback: try to load metadata if persisted in future versions
            raise KeyError(f"Rule parameters for hash {rule_hash} not found in index.")
        return rp

    def apply_rule(self, x: float, params: RuleParameters) -> float:
        """Apply one step of the generalized Collatz rule with numerical stability checks"""
        try:
            result = params.k * x + params.b

            if params.modulus is not None:
                result = result % params.modulus
            else:
                result /= params.divisor

            if not np.isfinite(result):
                return float("inf") if result > 0 else float("-inf")
            return float(result)
        except FloatingPointError:
            return float("inf")

    # --- analysis helpers ---
    def _compute_lyapunov(self, trajectory: List[float]) -> float:
        """
        Estimate the Lyapunov exponent using a robust numerical method
        λ = lim_{n→∞} (1/n) Σ log|Δx_n / x_{n-1}| (finite-diff proxy)
        """
        if len(trajectory) < 2:
            return 0.0
        logs: List[float] = []
        for i in range(1, len(trajectory)):
            x_prev, x_curr = trajectory[i - 1], trajectory[i]
            if x_prev == 0 or not np.isfinite(x_prev) or not np.isfinite(x_curr):
                continue
            deriv = abs((x_curr - x_prev) / x_prev)
            if deriv > 1e-12:  # avoid log(0)
                logs.append(log(deriv))
        return float(np.mean(logs)) if logs else 0.0

    def _detect_attractor(self, trajectory: List[float], params: RuleParameters) -> Optional[AttractorProperties]:
        """Advanced attractor detection with stability analysis"""
        window = min(CYCLE_DETECTION_WINDOW, len(trajectory) // 2 or 1)
        last_values = trajectory[-window:]

        # Check for fixed point
        rounded = [round(v, params.precision) for v in last_values if np.isfinite(v)]
        if len(rounded) >= 1 and len(set(rounded)) == 1:
            return AttractorProperties(cycle_length=1, stability=self._calculate_stability(trajectory))

        # Check for cycles
        for cycle_len in range(2, max(2, window // 2 + 1)):
            if self._is_cycle(trajectory, cycle_len, params.precision):
                return AttractorProperties(cycle_length=cycle_len, stability=self._calculate_stability(trajectory))
        return None

    def _is_cycle(self, trajectory: List[float], length: int, precision: int) -> bool:
        """Check if the trajectory ends in a cycle of given length"""
        if len(trajectory) < 2 * length:
            return False
        a = trajectory[-length:]
        b = trajectory[-2 * length : -length]
        return all(round(a[i], precision) == round(b[i], precision) for i in range(length))

    def _calculate_stability(self, trajectory: List[float]) -> float:
        """Calculate attractor stability (0=unstable, 1=perfectly stable)"""
        tail = [v for v in trajectory[-100:] if np.isfinite(v)]
        if len(tail) < 2:
            return 0.0
        diffs = np.abs(np.diff(tail))
        if not diffs.any():
            return 1.0
        return float(1 / (1 + float(np.mean(diffs))))

    def _compress_sequence(self, sequence: str) -> int:
        """Calculate compressed size of symbolic sequence (base64(gzip))"""
        if not sequence:
            return 0
        compressed = gzip.compress(sequence.encode(), compresslevel=COMPRESSION_LEVEL)
        return len(base64.b64encode(compressed).decode())

    def _calculate_entropy(self, symbols: Iterable[str]) -> float:
        """Shannon entropy (bits) of a symbol stream."""
        seq = list(symbols)
        n = len(seq)
        if n == 0:
            return 0.0
        counts = Counter(seq)
        probs = [c / n for c in counts.values()]
        return float(-sum(p * np.log2(p) for p in probs if p > 0))

    def _classify_cyclic(self, attractor: Optional[AttractorProperties]) -> SystemBehavior:
        if not attractor:
            return SystemBehavior.UNKNOWN
        return SystemBehavior.CYCLIC_LONG if attractor.cycle_length >= 100 else SystemBehavior.CYCLIC_SHORT

    # --- caching helpers ---
    def _enforce_cache_limit(self) -> None:
        try:
            files = [os.path.join(self.cache_dir, f) for f in os.listdir(self.cache_dir) if f.endswith('.joblib')]
            if len(files) <= MAX_CACHE_SIZE:
                return
            # prune oldest 10%
            files.sort(key=lambda p: os.path.getmtime(p))
            target = int(len(files) * 0.1)
            for p in files[:target]:
                try:
                    os.remove(p)
                except OSError:
                    pass
        except Exception:
            # best-effort; do not interrupt computation
            pass

    # --- primary computations ---
    def compute_trajectory(self, seed: Union[int, float], params: RuleParameters) -> TrajectoryResult:
        """Compute the full trajectory with enhanced diagnostics (cached)."""
        self.register_rule(params)
        cache_key = f"{params.rule_hash}_{seed}"
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.joblib")

        if os.path.exists(cache_file):
            try:
                return load(cache_file)
            except Exception as e:
                self.console.log(f"Cache load failed: {e}, recomputing…")

        x = float(seed)
        trajectory: List[float] = [x]
        parity_sequence: List[str] = []
        max_value = min_value = x
        behavior: SystemBehavior = SystemBehavior.UNKNOWN

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for iteration in track(range(params.max_iterations), description=f"Seed {seed}"):
                x = self.apply_rule(x, params)
                trajectory.append(x)

                # Update tracking variables
                if not np.isfinite(x):
                    behavior = SystemBehavior.DIVERGES_POSITIVE if x > 0 else SystemBehavior.DIVERGES_NEGATIVE
                    break
                # robust parity on floats (treat near-integers sanely)
                xi = int(abs(np.floor(x + 1e-9)))
                parity_sequence.append('E' if xi % 2 == 0 else 'O')

                if x > max_value:
                    max_value = x
                if x < min_value:
                    min_value = x

                # Termination conditions
                if abs(x - 1.0) < 1e-10:
                    behavior = SystemBehavior.CONVERGES
                    break
                if x > params.escape_threshold:
                    behavior = SystemBehavior.DIVERGES_POSITIVE
                    break
                if x < -params.escape_threshold:
                    behavior = SystemBehavior.DIVERGES_NEGATIVE
                    break
                if len(trajectory) > CYCLE_DETECTION_WINDOW and self._is_cycle(trajectory, 1, params.precision):
                    behavior = SystemBehavior.CYCLIC_SHORT
                    break
            else:
                # max iterations reached without classification → UNKNOWN
                iteration = params.max_iterations

        # Diagnostics
        lyapunov = self._compute_lyapunov(trajectory)
        attractor = self._detect_attractor(trajectory, params)
        entropy = self._calculate_entropy(parity_sequence)
        compressed_size = self._compress_sequence(''.join(parity_sequence))

        # Enhanced classification
        if behavior in (SystemBehavior.UNKNOWN, SystemBehavior.CYCLIC):
            cyc = self._classify_cyclic(attractor)
            if cyc != SystemBehavior.UNKNOWN:
                behavior = cyc
        if lyapunov > CHAOS_THRESHOLD:
            behavior = SystemBehavior.CHAOTIC

        result = TrajectoryResult(
            seed=seed,
            rule_hash=params.rule_hash,
            behavior=behavior,
            stopping_time=iteration if behavior == SystemBehavior.CONVERGES else None,
            max_value=max_value,
            min_value=min_value,
            parity_sequence=''.join(parity_sequence),
            entropy=entropy,
            lyapunov_exponent=lyapunov,
            trajectory=trajectory,
            compressed_size=compressed_size,
            attractor=attractor,
        )

        # Cache result with atomic write
        temp_file = cache_file + ".tmp"
        dump(result, temp_file, compress=3)
        os.replace(temp_file, cache_file)
        self._enforce_cache_limit()
        return result

    def parameter_sweep(self, param_grid: Dict[str, Iterable[Any]], seeds: List[Union[int, float]]) -> Dict[Tuple[Any, ...], List[TrajectoryResult]]:
        """Perform a multidimensional parameter sweep with progress tracking"""
        from itertools import product

        param_names = list(param_grid.keys())
        param_values = list(product(*param_grid.values()))
        total_combinations = len(param_values) * len(seeds)

        results: Dict[Tuple[Any, ...], List[TrajectoryResult]] = {}
        start_time = time.time()

        with self.console.status("[bold green]Processing parameter sweep…"):
            for combo in param_values:
                params_kwargs = dict(zip(param_names, combo))
                params = RuleParameters(**params_kwargs)
                self.register_rule(params)
                key = tuple(combo)
                results[key] = []
                for seed in seeds:
                    res = self.compute_trajectory(seed, params)
                    results[key].append(res)

        elapsed = time.time() - start_time
        self.console.print(f"Completed {total_combinations} combinations in {elapsed:.2f}s")
        return results

    # --- ML ---
    def train_models(self, results: Dict[Tuple[Any, ...], List[TrajectoryResult]], shap_enabled: bool = False) -> None:
        """Train classifier (behavior) and regressor (Lyapunov) with feature engineering"""
        X: List[List[float]] = []
        y_behavior: List[SystemBehavior] = []
        y_lyapunov: List[float] = []

        for _params_tuple, trajectories in results.items():
            for traj in trajectories:
                features = self._extract_features(traj)
                X.append(features)
                y_behavior.append(traj.behavior)
                y_lyapunov.append(traj.lyapunov_exponent)

        X = np.array(X)
        self.label_encoder.fit(y_behavior)
        y_behavior_encoded = self.label_encoder.transform(y_behavior)
        y_lyapunov_arr = np.array(y_lyapunov)

        X_train, X_test, yb_train, yb_test, yl_train, yl_test = train_test_split(
            X, y_behavior_encoded, y_lyapunov_arr, test_size=0.2, random_state=42
        )

        # Classifier
        self.classifier.fit(X_train, yb_train)
        yb_pred = self.classifier.predict(X_test)
        self.console.print("\n[bold]Behavior Classifier Report:")
        target_names = [c.name if isinstance(c, SystemBehavior) else str(c) for c in self.label_encoder.classes_]
        self.console.print(classification_report(yb_test, yb_pred, target_names=target_names))

        # Regressor
        self.regressor.fit(X_train, yl_train)
        yl_pred = self.regressor.predict(X_test)
        r2 = r2_score(yl_test, yl_pred)
        self.console.print(f"\n[bold]Lyapunov Regressor R²: {r2:.3f}")

        self.models_trained = True

        if shap_enabled or ("--shap" in sys.argv):
            self._run_shap_analysis(X_train)

    def _run_shap_analysis(self, X_train: np.ndarray) -> None:
        """Perform SHAP analysis on trained models (classifier)."""
        self.console.print("\n[bold cyan]Running SHAP analysis…")
        explainer = shap.TreeExplainer(self.classifier)
        sample = X_train[: min(1000, len(X_train))]
        shap_values = explainer.shap_values(sample)

        plt.figure(figsize=(12, 8))
        shap.summary_plot(
            shap_values,
            sample,
            feature_names=[
                "seed",
                "k",
                "b",
                "divisor",
                "entropy",
                "compression_ratio",
                "initial_slope",
                "parity_ratio",
                "lyapunov",
                "length",
                "max_value",
                "min_value",
            ],
            class_names=[c.name for c in self.label_encoder.classes_],
            show=False,
        )
        plt.tight_layout()
        plt.savefig("shap_summary.png")
        self.console.print("[green]SHAP summary plot saved to shap_summary.png")

    def _extract_features(self, trajectory: TrajectoryResult) -> List[float]:
        """Enhanced feature extraction for ML models."""
        try:
            params = self._load_rule_params(trajectory.rule_hash)
        except KeyError:
            # Fallback to neutral values if params unknown (should not occur)
            params = RuleParameters(k=0.0, b=0.0, divisor=1.0)

        seq_len = max(1, len(trajectory.parity_sequence))
        first_n = trajectory.trajectory[: min(10, len(trajectory.trajectory))]
        if len(first_n) >= 2:
            slope, _, _, _, _ = stats.linregress(range(len(first_n)), first_n)
        else:
            slope = 0.0

        entropy = trajectory.entropy
        compression_ratio = trajectory.compressed_size / seq_len
        parity_ratio = trajectory.parity_sequence.count('E') / seq_len

        return [
            float(trajectory.seed),
            float(params.k),
            float(params.b),
            float(params.divisor),
            float(entropy),
            float(compression_ratio),
            float(slope),
            float(parity_ratio),
            float(trajectory.lyapunov_exponent),
            float(len(trajectory.trajectory)),
            float(trajectory.max_value),
            float(trajectory.min_value),
        ]


# --------------------------
# Enhanced Visualization
# --------------------------

class BoundaryVisualizer:
    @staticmethod
    def plot_3d_surface(
        results: Dict[Tuple[Any, ...], List[TrajectoryResult]],
        x_param: str = "k",
        y_param: str = "b",
        z_metric: str = "convergence",
    ) -> None:
        """Interactive 3D surface plot of results"""
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (needed for 3D projection import side‑effect)

        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection="3d")

        x_vals: List[float] = []
        y_vals: List[float] = []
        z_vals: List[float] = []

        for params_tuple, trajectories in results.items():
            # Attempt to unpack common ordering (k, b, divisor[, modulus])
            k = params_tuple[0] if len(params_tuple) >= 1 else np.nan
            b = params_tuple[1] if len(params_tuple) >= 2 else np.nan
            divisor = params_tuple[2] if len(params_tuple) >= 3 else np.nan

            def pick(name: str) -> float:
                return {"k": k, "b": b, "divisor": divisor}.get(name, np.nan)

            x = pick(x_param)
            y = pick(y_param)

            if z_metric == "convergence":
                z = sum(1 for t in trajectories if t.behavior == SystemBehavior.CONVERGES) / max(1, len(trajectories))
            elif z_metric == "lyapunov":
                z = float(np.mean([t.lyapunov_exponent for t in trajectories]))
            elif z_metric == "entropy":
                z = float(np.mean([t.entropy for t in trajectories]))
            else:
                z = float(np.mean([len(t.trajectory) for t in trajectories]))

            x_vals.append(x)
            y_vals.append(y)
            z_vals.append(z)

        ax.plot_trisurf(x_vals, y_vals, z_vals, cmap="viridis", edgecolor="none")
        ax.set_xlabel(x_param)
        ax.set_ylabel(y_param)
        ax.set_zlabel(z_metric)
        plt.title(f"{z_metric} vs {x_param} and {y_param}")
        plt.show()

    @staticmethod
    def plot_heatmap(
        results: Dict[Tuple[Any, ...], List[TrajectoryResult]],
        x_param: str = "k",
        y_param: str = "seed",
    ) -> None:
        """Heatmap of convergence probability or entropy by chosen axes"""
        # Build grid
        data: Dict[Tuple[float, float], Tuple[float, float]] = {}
        x_set, y_set = set(), set()
        for params_tuple, trajectories in results.items():
            k = params_tuple[0] if len(params_tuple) >= 1 else np.nan
            b = params_tuple[1] if len(params_tuple) >= 2 else np.nan
            divisor = params_tuple[2] if len(params_tuple) >= 3 else np.nan

            for traj in trajectories:
                x = {
                    "k": float(k),
                    "b": float(b),
                    "divisor": float(divisor),
                    "seed": float(traj.seed),
                }[x_param]
                y = {
                    "k": float(k),
                    "b": float(b),
                    "divisor": float(divisor),
                    "seed": float(traj.seed),
                }[y_param]
                x_set.add(x)
                y_set.add(y)
                data[(x, y)] = (
                    1.0 if traj.behavior == SystemBehavior.CONVERGES else 0.0,
                    float(traj.entropy),
                )

        x_vals = sorted(x_set)
        y_vals = sorted(y_set)
        conv_grid = np.zeros((len(y_vals), len(x_vals)))
        entropy_grid = np.zeros((len(y_vals), len(x_vals)))

        for i, y in enumerate(y_vals):
            for j, x in enumerate(x_vals):
                if (x, y) in data:
                    conv_grid[i, j], entropy_grid[i, j] = data[(x, y)]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        im1 = ax1.imshow(
            conv_grid,
            extent=[min(x_vals), max(x_vals), min(y_vals), max(y_vals)],
            aspect="auto",
            cmap="RdYlGn",
            origin="lower",
        )
        ax1.set_title(f"Convergence: {x_param} vs {y_param}")
        ax1.set_xlabel(x_param)
        ax1.set_ylabel(y_param)
        fig.colorbar(im1, ax=ax1, label="Convergence Probability")

        im2 = ax2.imshow(
            entropy_grid,
            extent=[min(x_vals), max(x_vals), min(y_vals), max(y_vals)],
            aspect="auto",
            cmap="viridis",
            origin="lower",
        )
        ax2.set_title(f"Entropy: {x_param} vs {y_param}")
        ax2.set_xlabel(x_param)
        fig.colorbar(im2, ax=ax2, label="Entropy")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_combined_heatmap(
        results: Dict[Tuple[Any, ...], List[TrajectoryResult]], x_param: str = "k", y_param: str = "seed"
    ) -> None:
        """Retained for back-compat (alias to plot_heatmap with dual panels)."""
        return BoundaryVisualizer.plot_heatmap(results, x_param=x_param, y_param=y_param)


# --------------------------
# CLI Interface
# --------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Symbolic Decision Boundary Engine v2.1",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sweep command
    sweep_parser = subparsers.add_parser("sweep", help="Perform parameter sweep")
    sweep_parser.add_argument("--k-range", type=float, nargs=3, metavar=("START", "END", "STEP"),
                              default=[2.9, 3.1, 0.01], help="Range for k parameter")
    sweep_parser.add_argument("--b-range", type=float, nargs=3, metavar=("START", "END", "STEP"),
                              default=[0.5, 1.5, 0.05], help="Range for b parameter")
    sweep_parser.add_argument("--divisor-range", type=float, nargs=3, metavar=("START", "END", "STEP"),
                              default=[1.9, 2.1, 0.01], help="Range for divisor parameter")
    sweep_parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 11)), help="Seeds to test")
    sweep_parser.add_argument("--modulus", type=int, default=None, help="Modulus to apply (optional)")
    sweep_parser.add_argument("--output", type=str, default="sweep_results.joblib", help="Output file for results")
    sweep_parser.add_argument("--json", action="store_true", help="Also emit results JSON next to .joblib")

    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Visualize results")
    viz_parser.add_argument("--input", type=str, required=True, help="Input file with results (.joblib)")
    viz_parser.add_argument("--plot-type", choices=["heatmap", "3d", "combined"], default="heatmap",
                            help="Type of visualization")
    viz_parser.add_argument("--x-param", default="k", choices=["k", "b", "divisor", "seed"], help="X axis")
    viz_parser.add_argument("--y-param", default="seed", choices=["k", "b", "divisor", "seed"], help="Y axis")
    viz_parser.add_argument("--z-metric", default="convergence",
                            choices=["convergence", "lyapunov", "entropy", "length"],
                            help="Metric for z-axis in 3D plots")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train ML models")
    train_parser.add_argument("--input", type=str, required=True, help="Input file with results (.joblib)")
    train_parser.add_argument("--shap", action="store_true", help="Generate SHAP explainability plots")

    args = parser.parse_args()
    engine = SymbolicBoundaryEngine()
    visualizer = BoundaryVisualizer()

    if args.command == "sweep":
        # Build parameter grid
        param_grid: Dict[str, Iterable[Any]] = {
            "k": np.arange(*args.k_range),
            "b": np.arange(*args.b_range),
            "divisor": np.arange(*args.divisor_range),
        }
        if args.modulus is not None:
            param_grid["modulus"] = [args.modulus]
        results = engine.parameter_sweep(param_grid, args.seeds)

        dump(results, args.output, compress=3)
        if args.json:
            json_results = []
            for params_tuple, trajectories in results.items():
                # decode params tuple in the same order we constructed the grid
                rec: Dict[str, Any] = {}
                keys = list(param_grid.keys())
                for i, key in enumerate(keys):
                    if i < len(params_tuple):
                        rec[key] = params_tuple[i]
                json_results.append({
                    "parameters": rec,
                    "results": [{
                        "seed": t.seed,
                        "behavior": t.behavior.name,
                        "stopping_time": t.stopping_time,
                        "entropy": t.entropy,
                        "lyapunov": t.lyapunov_exponent,
                        "compression_ratio": (t.compressed_size / max(1, len(t.parity_sequence))),
                    } for t in trajectories],
                })
            json_path = args.output.replace('.joblib', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2)

    elif args.command == "visualize":
        results = load(args.input)
        if args.plot_type == "3d":
            visualizer.plot_3d_surface(results, args.x_param, args.y_param, args.z_metric)
        elif args.plot_type == "combined":
            visualizer.plot_combined_heatmap(results, args.x_param, args.y_param)
        else:
            visualizer.plot_heatmap(results, args.x_param, args.y_param)

    elif args.command == "train":
        results = load(args.input)
        engine.train_models(results, shap_enabled=args.shap)


if __name__ == "__main__":
    main()
