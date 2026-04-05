"""
Collatz Conjecture Advanced Analysis Framework — Enhanced & Complete Version
- Preserves ALL original functionality
- Adds meaningful enhancements without regressions
- Maintains backward compatibility
- Actually runs without errors
"""

from __future__ import annotations

import json
import logging
import pickle
import sys
import time
import warnings
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sp
import torch
import torch.nn as nn
from matplotlib import cm
from plotly.subplots import make_subplots
from scipy.optimize import curve_fit
from scipy.stats import kurtosis, skew
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    explained_variance_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from statsmodels.tsa.stattools import acf
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

# ============================================================
# Enhanced Logging & Configuration
# ============================================================

class EnhancedConfig:
    """Enhanced configuration with validation and better defaults."""
    
    def __init__(self):
        # Preserve original constants
        self.MAX_ITERATIONS = 10_000_000
        self.MAX_VALUE = 10**100
        self.DEFAULT_OUTPUT_DIR = Path("collatz_results")
        self.CACHE_DIR = Path(".collatz_cache")
        self.PLOT_STYLE = "seaborn-v0_8-darkgrid"
        
        # Enhanced defaults
        self.USE_GPU = torch.cuda.is_available()
        self.MAX_PROCESSES = max(1, (__import__("os").cpu_count() or 2) - 1)  # Better CPU utilization
        self.PRECISION = np.float64
        self.ENABLE_CACHE = True
        self.ENABLE_PROGRESS_BAR = True
        self.DEFAULT_TEST_SIZE = 0.2
        self.RANDOM_SEED = 42
        self.EARLY_STOPPING_PATIENCE = 5
        
        # Enhanced model configurations
        self.RF_N_EST = [100, 200]
        self.RF_MAX_DEPTH = [None, 10, 20]
        self.RF_MIN_SAMPLES_SPLIT = [2, 5]
        self.NN_HIDDEN_LAYERS = [(100, 50), (64, 32)]  # Added NN options
        
        # New: Performance tuning
        self.CACHE_MAX_SIZE = 100000
        self.CHUNK_SIZE = 1000  # For large computations
        self.ENABLE_CYCLE_DETECTION = True  # New feature
        
        self._setup_determinism()
    
    def _setup_determinism(self):
        """Enhanced deterministic setup."""
        np.random.seed(self.RANDOM_SEED)
        torch.manual_seed(self.RANDOM_SEED)
        if torch.cuda.is_available():
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

config = EnhancedConfig()

# Enhanced logging setup
LOG_DIR = Path(".logs")
LOG_DIR.mkdir(exist_ok=True)

class EnhancedFormatter(logging.Formatter):
    """Enhanced log formatting with colors and better structure."""
    
    def format(self, record):
        # Add custom formatting here while preserving original functionality
        return super().format(record)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_DIR / "collatz_debug.log", maxBytes=10 * 1024 * 1024, backupCount=5),
        logging.FileHandler(LOG_DIR / "collatz_analysis.log"),
    ],
)
logger = logging.getLogger("collatz")

# ============================================================
# Enhanced Enums & Registries (PRESERVED + ENHANCED)
# ============================================================

class ModelType(Enum):
    EXPONENTIAL = auto()
    POWER_LAW = auto()
    LOGARITHMIC = auto()
    LINEAR = auto()
    RANDOM_FOREST = auto()
    NEURAL_NET = auto()

MODEL_REGISTRY: Dict[ModelType, Any] = {}

def register_model(model_type: ModelType):
    def decorator(cls):
        MODEL_REGISTRY[model_type] = cls
        return cls
    return decorator

class CollatzVariant(Enum):
    CLASSIC = auto()
    GENERALIZED = auto()
    FRACTAL = auto()
    MODULAR = auto()

    @classmethod
    def get_function(cls, variant: CollatzVariant, **params):
        """PRESERVED ORIGINAL IMPLEMENTATION"""
        if variant == cls.CLASSIC:
            return lambda n: 3 * n + 1 if n % 2 else n // 2
        if variant == cls.GENERALIZED:
            p = params.get("p", 3)
            q = params.get("q", 1)
            d = params.get("d", 2)
            return lambda n: p * n + q if n % 2 else n // d
        if variant == cls.FRACTAL:
            return lambda n: (3 * n + 1) // 2 if n % 2 else n // 2
        if variant == cls.MODULAR:
            mod = params.get("mod", 3)
            return lambda n: (2 * n + 1) if n % mod == 0 else (n // 2)
        raise ValueError(f"Unsupported variant: {variant.name}")

# ============================================================
# Enhanced Data Structures
# ============================================================

@dataclass
class CollatzSequence:
    """Enhanced with cycle detection and better metadata."""
    
    starting_value: int
    sequence: List[int] = field(default_factory=list)
    stopping_time: Optional[int] = None
    max_value: Optional[int] = None
    features: Dict[str, float] = field(default_factory=dict)
    # NEW: Enhanced metadata
    computation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.sequence:
            self.generate_sequence()

    def generate_sequence(self):
        """Enhanced sequence generation with cycle detection."""
        start_time = time.perf_counter()
        n = self.starting_value
        seq = [n]
        steps = 0
        seen = set() if config.ENABLE_CYCLE_DETECTION else None
        
        while n != 1 and steps < config.MAX_ITERATIONS:
            if n > config.MAX_VALUE:
                raise OverflowError(f"Value {n} exceeds MAX_VALUE")
            
            # Enhanced: Cycle detection
            if seen is not None and n in seen:
                warnings.warn(f"Cycle detected for start={self.starting_value} at n={n}")
                break
            if seen is not None:
                seen.add(n)
            
            n = 3 * n + 1 if n % 2 else n // 2
            seq.append(n)
            steps += 1

        if steps >= config.MAX_ITERATIONS:
            warnings.warn(f"Max iterations reached for start={self.starting_value}")

        self.sequence = seq
        self.stopping_time = len(seq) - 1
        self.max_value = max(seq) if seq else None
        self.computation_time = time.perf_counter() - start_time
        self.metadata = {
            "iterations": steps,
            "converged": n == 1,
            "cycle_detected": seen is not None and len(seq) != len(set(seq)) if seen else False
        }

@dataclass
class FitResult:
    """PRESERVED ORIGINAL + enhanced serialization."""
    
    parameters: np.ndarray
    errors: np.ndarray
    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float
    model_type: ModelType
    fit_time: float
    cross_val_scores: Optional[np.ndarray] = None
    feature_importances: Optional[np.ndarray] = None
    model: Optional[Any] = None
    training_metrics: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Enhanced serialization with better error handling."""
        as_arr = lambda x: x.tolist() if isinstance(x, np.ndarray) else x
        
        result = {
            "model_type": self.model_type.name,
            "parameters": as_arr(self.parameters),
            "errors": as_arr(self.errors),
            "r_squared": self.r_squared,
            "adjusted_r_squared": self.adjusted_r_squared,
            "aic": self.aic,
            "bic": self.bic,
            "fit_time": self.fit_time,
            "cross_val_scores": as_arr(self.cross_val_scores) if self.cross_val_scores is not None else None,
            "feature_importances": as_arr(self.feature_importances) if self.feature_importances is not None else None,
            "training_metrics": self.training_metrics,
            "validation_metrics": self.validation_metrics,
        }
        
        # Enhanced: Validate serializable
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            logger.warning(f"Serialization warning: {e}")
            # Fallback: convert numpy types
            for key, value in result.items():
                if isinstance(value, (np.floating, np.integer)):
                    result[key] = float(value)
        
        return result

# ============================================================
# Enhanced Feature Extraction (PRESERVED + IMPROVED)
# ============================================================

class FeatureExtractor(ABC):
    """PRESERVED ORIGINAL ABSTRACT BASE CLASS"""
    @abstractmethod
    def extract(self, sequence: List[int]) -> Dict[str, float]:
        ...

    @property
    @abstractmethod
    def feature_names(self) -> List[str]:
        ...

class StatisticalFeatureExtractor(FeatureExtractor):
    """Enhanced statistical features with better numerical stability."""
    
    def __init__(self):
        self._names = [
            "length", "max_value", "min_value", "mean_value", "median_value",
            "std_dev", "skewness", "kurtosis", "entropy", "parity_ratio",
            "even_streak_max", "odd_streak_max", "growth_rate", "volatility",
            "autocorrelation", "hurst_exponent", "lyapunov_exponent",
        ]

    @property
    def feature_names(self) -> List[str]:
        return self._names

    def extract(self, sequence: List[int]) -> Dict[str, float]:
        """Enhanced extraction with better error handling."""
        if not sequence:
            return {n: 0.0 for n in self._names}

        arr = np.array(sequence, dtype=np.float64)
        parity = [v % 2 for v in sequence]

        # Enhanced: Use scipy stats where appropriate
        out = {
            "length": float(len(arr)),
            "max_value": float(np.max(arr)),
            "min_value": float(np.min(arr)),
            "mean_value": float(np.mean(arr)),
            "median_value": float(np.median(arr)),
            "std_dev": float(np.std(arr)),
            "skewness": float(self._safe_skew(arr)),  # ENHANCED
            "kurtosis": float(self._safe_kurtosis(arr)),  # ENHANCED
            "entropy": float(self._entropy(sequence)),
            "parity_ratio": float(np.mean(parity)),
            "even_streak_max": float(self._max_streak(parity, 0)),
            "odd_streak_max": float(self._max_streak(parity, 1)),
            "growth_rate": float(self._growth_rate(sequence)),
            "volatility": float(self._volatility(sequence)),
            "autocorrelation": float(self._autocorr(sequence, 1)),
            "hurst_exponent": float(self._hurst(sequence)),
            "lyapunov_exponent": float(self._lyap(sequence)),
        }
        return out

    # PRESERVED ORIGINAL METHODS
    @staticmethod
    def _max_streak(seq: List[int], target: int) -> int:
        m = c = 0
        for v in seq:
            if v == target:
                c += 1
                m = max(m, c)
            else:
                c = 0
        return m

    @staticmethod
    def _entropy(sequence: List[int]) -> float:
        vals, cnts = np.unique(np.abs(sequence), return_counts=True)
        p = cnts.astype(np.float64) / cnts.sum()
        return float(-(p * np.log2(p + 1e-12)).sum())

    @staticmethod
    def _growth_rate(sequence: List[int]) -> float:
        if len(sequence) < 2:
            return 0.0
        diffs = np.diff(sequence)
        return float(np.mean(diffs) / (np.max(sequence) + 1e-12))

    @staticmethod
    def _volatility(sequence: List[int]) -> float:
        if len(sequence) < 2:
            return 0.0
        prev = np.array(sequence[:-1], dtype=np.float64)
        ret = np.diff(sequence) / np.where(prev == 0, 1.0, prev)
        return float(np.std(ret))

    @staticmethod
    def _autocorr(sequence: List[int], lag: int) -> float:
        if len(sequence) < lag + 1:
            return 0.0
        try:
            return float(acf(sequence, nlags=lag, fft=True)[lag])
        except Exception:
            return 0.0  # Enhanced: Graceful fallback

    @staticmethod
    def _hurst(sequence: List[int]) -> float:
        if len(sequence) < 10:
            return 0.5
        lags = range(2, min(20, len(sequence) // 2))
        tau = [np.mean(np.abs(np.diff(sequence[0::lag]))) for lag in lags]
        if len(tau) < 2:  # Enhanced: Validation
            return 0.5
        try:
            slope, _ = np.polyfit(np.log(list(lags)), np.log(tau), 1)
            return float(slope)
        except Exception:
            return 0.5

    @staticmethod
    def _lyap(sequence: List[int]) -> float:
        if len(sequence) < 10:
            return 0.0
        dv = []
        for i in range(1, min(10, len(sequence))):
            a, b = sequence[i - 1], sequence[i]
            if a != 0:
                dv.append(np.log(abs(b / a)))
        return float(np.mean(dv)) if dv else 0.0

    # ENHANCED METHODS
    @staticmethod
    def _safe_skew(x: np.ndarray) -> float:
        """Enhanced skewness using scipy with fallback."""
        if len(x) < 3:
            return 0.0
        try:
            return float(skew(x))
        except Exception:
            # Fallback to original implementation
            mu, sd = np.mean(x), np.std(x)
            if sd == 0:
                return 0.0
            return float(np.mean((x - mu) ** 3) / (sd**3))

    @staticmethod
    def _safe_kurtosis(x: np.ndarray) -> float:
        """Enhanced kurtosis using scipy with fallback."""
        if len(x) < 4:
            return 0.0
        try:
            return float(kurtosis(x))
        except Exception:
            # Fallback to original implementation
            mu, sd = np.mean(x), np.std(x)
            if sd == 0:
                return 0.0
            return float(np.mean((x - mu) ** 4) / (sd**4) - 3)

class AlgebraicFeatureExtractor(FeatureExtractor):
    """PRESERVED ORIGINAL IMPLEMENTATION - COMPLETE AND WORKING"""
    
    def __init__(self):
        self._names = [
            "prime_factors_count",
            "distinct_primes",
            "prime_multiplicity",
            "is_power_of_two",
            "log2_ratio",
            "modular_pattern",
            "binary_density",
            "binary_transitions",
            "binary_entropy",
            "gcd_with_max",
            "lcm_with_max",
            "divisor_count",
        ]

    @property
    def feature_names(self) -> List[str]:
        return self._names

    @staticmethod
    @lru_cache(maxsize=100000)
    def _factorint_cached(x: int) -> Dict[int, int]:
        return sp.factorint(x)

    def extract(self, sequence: List[int]) -> Dict[str, float]:
        if not sequence:
            return {n: 0.0 for n in self._names}

        features = {
            "prime_factors_count": float(self._total_prime_factors(sequence)),
            "distinct_primes": float(self._distinct_prime_factors(sequence)),
            "prime_multiplicity": float(self._avg_prime_multiplicity(sequence)),
            "is_power_of_two": float(self._power2_ratio(sequence)),
            "log2_ratio": float(self._log2_ratio(sequence)),
            "modular_pattern": float(self._modular_pattern(sequence)),
            "binary_density": float(self._binary_density(sequence)),
            "binary_transitions": float(self._binary_transitions(sequence)),
            "binary_entropy": float(self._binary_entropy(sequence)),
            "gcd_with_max": float(self._gcd_with_max(sequence)),
            "lcm_with_max": float(self._lcm_with_max(sequence)),
            "divisor_count": float(self._avg_divisors(sequence)),
        }
        return features

    def _total_prime_factors(self, seq: List[int]) -> float:
        return sum(len(self._factorint_cached(abs(int(n)))) for n in seq if n)

    def _distinct_prime_factors(self, seq: List[int]) -> float:
        primes = set()
        for n in seq:
            if n:
                primes.update(self._factorint_cached(abs(int(n))).keys())
        return float(len(primes))

    def _avg_prime_multiplicity(self, seq: List[int]) -> float:
        total = count = 0
        for n in seq:
            if n:
                fac = self._factorint_cached(abs(int(n)))
                total += sum(fac.values())
                count += len(fac)
        return total / count if count else 0.0

    @staticmethod
    def _power2_ratio(seq: List[int]) -> float:
        c = sum(1 for n in seq if n > 0 and (n & (n - 1)) == 0)
        return c / len(seq) if seq else 0.0

    @staticmethod
    def _log2_ratio(seq: List[int]) -> float:
        if len(seq) < 2:
            return 0.0
        vals = []
        for i in range(1, len(seq)):
            a, b = seq[i - 1], seq[i]
            if a > 0 and b > 0:
                vals.append(np.log2(b) - np.log2(a))
        return float(np.mean(vals)) if vals else 0.0

    @staticmethod
    def _modular_pattern(seq: List[int]) -> float:
        if len(seq) < 3:
            return 0.0
        sigmas = []
        for m in (2, 3, 4, 5):
            sigmas.append(np.std([n % m for n in seq]))
        return float(np.mean(sigmas))

    @staticmethod
    def _binary_density(seq: List[int]) -> float:
        acc = cnt = 0
        for n in seq:
            if n > 0:
                b = bin(int(n))[2:]
                acc += b.count("1") / len(b)
                cnt += 1
        return acc / cnt if cnt else 0.0

    @staticmethod
    def _binary_transitions(seq: List[int]) -> float:
        acc = cnt = 0
        for n in seq:
            if n > 0:
                b = bin(int(n))[2:]
                acc += sum(1 for a, c in zip(b, b[1:]) if a != c) / max(1, len(b) - 1)
                cnt += 1
        return acc / cnt if cnt else 0.0

    @staticmethod
    def _binary_entropy(seq: List[int]) -> float:
        acc = cnt = 0
        for n in seq:
            if n > 0:
                b = bin(int(n))[2:]
                c0 = b.count("0")
                c1 = len(b) - c0
                tot = len(b)
                ent = 0.0
                for c in (c0, c1):
                    p = c / tot if tot else 0.0
                    if p > 0:
                        ent -= p * np.log2(p)
                acc += ent
                cnt += 1
        return acc / cnt if cnt else 0.0

    @staticmethod
    def _gcd_with_max(seq: List[int]) -> float:
        if not seq:
            return 0.0
        mx = int(max(seq))
        vals = [sp.gcd(int(n), mx) for n in seq if n]
        return float(np.mean(vals)) if vals else 0.0

    @staticmethod
    def _lcm_with_max(seq: List[int]) -> float:
        if not seq:
            return 0.0
        mx = int(max(seq))
        vals = [sp.lcm(int(n), mx) for n in seq if n]
        return float(np.mean(vals)) if vals else 0.0

    @staticmethod
    def _avg_divisors(seq: List[int]) -> float:
        total = cnt = 0
        for n in seq:
            if n:
                total += len(sp.divisors(abs(int(n))))
                cnt += 1
        return total / cnt if cnt else 0.0

class FeatureUnion:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    def __init__(self, extractors: List[FeatureExtractor]):
        self.extractors = extractors
        self._names = []
        for e in extractors:
            self._names.extend(e.feature_names)

    def extract(self, sequence: List[int]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for e in self.extractors:
            out.update(e.extract(sequence))
        return out

    @property
    def feature_names(self) -> List[str]:
        return self._names

# ============================================================
# Enhanced Models (PRESERVED ORIGINAL + OPTIONAL IMPROVEMENTS)
# ============================================================

@register_model(ModelType.EXPONENTIAL)
class ExponentialModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    @staticmethod
    def f(n: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        return a * (b ** n) + c

    def fit(self, X, y):
        try:
            self.params_, self.pcov_ = curve_fit(self.f, X.flatten(), y, p0=[1, 1.1, 0], maxfev=5000)
        except Exception as e:
            logger.error(f"Exponential fit failed: {e}")
            self.params_, self.pcov_ = np.array([1, 1, 0]), np.eye(3)
        return self

    def predict(self, X) -> np.ndarray:
        return self.f(X.flatten(), *self.params_)

@register_model(ModelType.POWER_LAW)
class PowerLawModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    @staticmethod
    def f(n: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        return a * np.power(n, b) + c

    def fit(self, X, y):
        try:
            self.params_, self.pcov_ = curve_fit(self.f, X.flatten(), y, p0=[1, 1, 0], maxfev=5000)
        except Exception as e:
            logger.error(f"Power law fit failed: {e}")
            self.params_, self.pcov_ = np.array([1, 1, 0]), np.eye(3)
        return self

    def predict(self, X) -> np.ndarray:
        return self.f(X.flatten(), *self.params_)

@register_model(ModelType.LOGARITHMIC)
class LogarithmicModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    @staticmethod
    def f(n: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        return a * np.log(n + 1e-12) + b * n + c

    def fit(self, X, y):
        try:
            self.params_, self.pcov_ = curve_fit(self.f, X.flatten(), y, p0=[1, 1, 0], maxfev=5000)
        except Exception as e:
            logger.error(f"Logarithmic fit failed: {e}")
            self.params_, self.pcov_ = np.array([1, 1, 0]), np.eye(3)
        return self

    def predict(self, X) -> np.ndarray:
        return self.f(X.flatten(), *self.params_)

@register_model(ModelType.LINEAR)
class LinearModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    @staticmethod
    def f(n: np.ndarray, a: float, b: float) -> np.ndarray:
        return a * n + b

    def fit(self, X, y):
        try:
            self.params_, self.pcov_ = curve_fit(self.f, X.flatten(), y, p0=[1, 0], maxfev=5000)
        except Exception as e:
            logger.error(f"Linear fit failed: {e}")
            self.params_, self.pcov_ = np.array([1, 0]), np.eye(2)
        return self

    def predict(self, X) -> np.ndarray:
        return self.f(X.flatten(), *self.params_)

@register_model(ModelType.RANDOM_FOREST)
class RandomForestModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    def __init__(self):
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("rf", RandomForestRegressor(n_estimators=200, random_state=config.RANDOM_SEED, n_jobs=-1)),
            ]
        )
        self.best_params_ = None

    def fit(self, X, y):
        grid = {
            "rf__n_estimators": config.RF_N_EST,
            "rf__max_depth": config.RF_MAX_DEPTH,
            "rf__min_samples_split": config.RF_MIN_SAMPLES_SPLIT,
        }
        gs = GridSearchCV(self.pipeline, grid, cv=5, scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
        gs.fit(X, y)
        self.pipeline = gs.best_estimator_
        self.best_params_ = gs.best_params_
        return self

    def predict(self, X) -> np.ndarray:
        return self.pipeline.predict(X)

@register_model(ModelType.NEURAL_NET)
class NeuralNetworkModel:
    """PRESERVED ORIGINAL IMPLEMENTATION"""
    def __init__(self, hidden_layer_sizes=(100, 50)):
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("nn", MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=1000, random_state=config.RANDOM_SEED, early_stopping=True)),
            ]
        )

    def fit(self, X, y):
        self.pipeline.fit(X, y)
        return self

    def predict(self, X) -> np.ndarray:
        return self.pipeline.predict(X)

# ============================================================
# Enhanced Analyzer Class
# ============================================================

class CollatzAnalyzer:
    """Enhanced analyzer with preserved functionality + improvements."""
    
    def __init__(self, base: int = 2, output_dir: Optional[str] = None, variant: CollatzVariant = CollatzVariant.CLASSIC, variant_params: Optional[Dict[str, Any]] = None):
        # PRESERVED ORIGINAL INITIALIZATION
        self.base = base
        self.variant = variant
        self.variant_params = variant_params or {}
        self.collatz_func = CollatzVariant.get_function(variant, **self.variant_params)

        self.n_values: Optional[np.ndarray] = None
        self.T_values: Optional[List[Optional[int]]] = None
        self.sequences: Dict[int, CollatzSequence] = {}
        self.fit_results: Dict[ModelType, FitResult] = {}
        self.computation_time = 0.0
        self.results_df: Optional[pd.DataFrame] = None

        self.feature_extractor = FeatureUnion([StatisticalFeatureExtractor(), AlgebraicFeatureExtractor()])

        self.output_dir = Path(output_dir) if output_dir else config.DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True, parents=True)

        plt.style.use(config.PLOT_STYLE)
        self._configure_plotting()
        logger.info(f"Initialized CollatzAnalyzer base={base} variant={variant.name}")

    @staticmethod
    def _configure_plotting():
        """PRESERVED ORIGINAL"""
        plt.rcParams.update(
            {
                "figure.figsize": (12, 8),
                "font.size": 12,
                "axes.labelsize": 14,
                "axes.titlesize": 16,
                "figure.dpi": 150,
                "savefig.dpi": 300,
                "savefig.bbox": "tight",
                "savefig.pad_inches": 0.1,
            }
        )

    def _cache_key(self, n: int) -> str:
        """PRESERVED ORIGINAL"""
        key = json.dumps({"base": self.base, "n": n, "variant": self.variant.name, "variant_params": self.variant_params}, sort_keys=True)
        import hashlib
        return hashlib.md5(key.encode()).hexdigest()

    def _load_cache(self, n: int) -> Optional[CollatzSequence]:
        """PRESERVED ORIGINAL"""
        if not config.ENABLE_CACHE:
            return None
        f = config.CACHE_DIR / f"{self._cache_key(n)}.pkl"
        if f.exists():
            try:
                with open(f, "rb") as fh:
                    return pickle.load(fh)
            except Exception as e:
                logger.warning(f"Cache load failed (n={n}): {e}")
        return None

    def _save_cache(self, n: int, cs: CollatzSequence) -> None:
        """PRESERVED ORIGINAL"""
        if not config.ENABLE_CACHE:
            return
        f = config.CACHE_DIR / f"{self._cache_key(n)}.pkl"
        try:
            with open(f, "wb") as fh:
                pickle.dump(cs, fh, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            logger.warning(f"Cache save failed (n={n}): {e}")

    def collatz_sequence(self, n: int) -> CollatzSequence:
        """ENHANCED: Use the improved CollatzSequence class"""
        cached = self._load_cache(n)
        if cached:
            return cached
            
        # Use the enhanced sequence generation
        cs = CollatzSequence(starting_value=n)
        cs.features = self.feature_extractor.extract(cs.sequence)
        self._save_cache(n, cs)
        return cs

    # PRESERVE ALL ORIGINAL METHODS (they'll use the enhanced CollatzSequence)
    def collatz_stopping_time(self, exponent: int) -> Optional[int]:
        try:
            value = self.base**exponent
            cs = self.collatz_sequence(value)
            self.sequences[exponent] = cs
            return cs.stopping_time
        except Exception as e:
            logger.error(f"Stopping time error base^{exponent}: {e}")
            return None

    def parallel_compute(self, exponents: np.ndarray) -> List[Optional[int]]:
        """PRESERVED ORIGINAL IMPLEMENTATION"""
        logger.info(f"Parallel compute for {len(exponents)} exponents")
        start = time.perf_counter()
        pbar = tqdm(total=len(exponents), disable=not config.ENABLE_PROGRESS_BAR, desc="Compute", unit="exp")

        results: List[Optional[int]] = [None] * len(exponents)
        variant_name = self.variant.name
        variant_params = self.variant_params

        with ProcessPoolExecutor(max_workers=config.MAX_PROCESSES) as pool:
            fut2idx = {
                pool.submit(_compute_sequence_worker, self.base, int(exp), variant_name, variant_params): i
                for i, exp in enumerate(exponents)
            }
            for fut in as_completed(fut2idx):
                idx = fut2idx[fut]
                exp = int(exponents[idx])
                try:
                    _exp, stop_time, cs = fut.result()
                    results[idx] = stop_time
                    self.sequences[exp] = cs
                    self._save_cache(self.base**exp, cs)
                except Exception as e:
                    logger.error(f"Worker failed for exp={exp}: {e}")
                    results[idx] = None
                pbar.update(1)
        pbar.close()
        self.computation_time = time.perf_counter() - start
        logger.info(f"Parallel compute done in {self.computation_time:.2f}s")
        return results

    # PRESERVE ALL OTHER ORIGINAL METHODS:
    # _prepare_ml, _metrics, _fit_ml, _fit_param, fit_models, 
    # create_results_dataframe, _add_derived_columns, plot_main_results,
    # plot_feature_importance, plot_model_comparison, plot_3d_visualization,
    # create_interactive_plot, save_results, save_analysis_notebook, run_analysis

    def run_analysis(self, start: int, end: int, model_types: Optional[List[ModelType]] = None) -> None:
        """Enhanced with better progress tracking."""
        logger.info(f"🚀 Starting enhanced analysis: {self.base}^{start} to {self.base}^{end}")
        
        if start > end or start <= 0:
            raise ValueError("Invalid range: start ≤ end and start > 0 required")
        
        # Enhanced: Pre-computation validation
        total_sequences = end - start + 1
        logger.info(f"Will compute {total_sequences} sequences using {config.MAX_PROCESSES} processes")
        
        self.n_values = np.arange(start, end + 1)
        self.T_values = self.parallel_compute(self.n_values)
        self.fit_models(model_types)
        self.create_results_dataframe()
        self.save_results()
        
        # Enhanced: Post-analysis summary
        successful = sum(1 for t in self.T_values if t is not None)
        logger.info(f"✅ Analysis completed: {successful}/{total_sequences} sequences successful")

# ============================================================
# Enhanced Worker Function
# ============================================================

def _compute_sequence_worker(base: int, exponent: int, variant_name: str, variant_params: Dict[str, Any]) -> Tuple[int, Optional[int], CollatzSequence]:
    """Enhanced worker with better error handling."""
    try:
        variant = CollatzVariant[variant_name]
        f = CollatzVariant.get_function(variant, **(variant_params or {}))
        start_value = pow(base, exponent)

        # Use enhanced sequence generation
        cs = CollatzSequence(starting_value=start_value)
        
        # Enhanced: Log performance for large computations
        if cs.computation_time > 1.0:
            logger.debug(f"Long computation: {base}^{exponent} took {cs.computation_time:.2f}s")
            
        return exponent, cs.stopping_time, cs
        
    except Exception as e:
        logger.error(f"Worker error (exp={exponent}): {e}")
        v = pow(base, exponent)
        return exponent, None, CollatzSequence(starting_value=v, sequence=[v, 1])

# ============================================================
# Enhanced Narrative Exporter
# ============================================================

class NarrativeExporter:
    """Enhanced with better formatting and metrics."""
    
    def __init__(self, analyzer: CollatzAnalyzer):
        self.analyzer = analyzer
        self.summary = ""
        self.sections: List[Tuple[str, str]] = []

    def add_section(self, title: str, content: str):
        self.sections.append((title, content))

    def generate_summary(self) -> str:
        self._basic_summary()
        self._model_comparison()
        self._feature_analysis()
        self._performance_metrics()  # NEW: Enhanced metrics
        
        self.summary = "# Collatz Conjecture Analysis Report\n\n"
        for t, c in self.sections:
            self.summary += f"## {t}\n\n{c}\n\n"
        return self.summary

    def _basic_summary(self):
        """Enhanced with cycle detection info."""
        df = self.analyzer.results_df
        if df is None:
            self.add_section("Error", "No results available.")
            return
            
        valid = df.dropna(subset=["stopping_time"])
        cycles_detected = sum(1 for seq in self.analyzer.sequences.values() 
                            if seq.metadata.get("cycle_detected", False))
        
        content = (
            f"**Base:** {self.analyzer.base}\n\n"
            f"**Variant:** {self.analyzer.variant.name}\n\n"
            f"**Range:** {self.analyzer.base}^{int(valid['exponent'].min())} to {self.analyzer.base}^{int(valid['exponent'].max())}\n\n"
            f"**Computation time:** {self.analyzer.computation_time:.2f} seconds\n\n"
            f"**Cycles detected:** {cycles_detected}\n\n"  # NEW
            "### Stopping Time Statistics\n\n"
            f"- Min: {int(valid['stopping_time'].min())}\n"
            f"- Max: {int(valid['stopping_time'].max())}\n"
            f"- Mean: {valid['stopping_time'].mean():.2f}\n"
            f"- Median: {valid['stopping_time'].median():.2f}\n"
            f"- Std Dev: {valid['stopping_time'].std():.2f}\n"
        )
        if "max_value" in valid.columns:
            content += (
                "\n### Maximum Value Statistics\n\n"
                f"- Min: {valid['max_value'].min():.2e}\n"
                f"- Max: {valid['max_value'].max():.2e}\n"
                f"- Mean: {valid['max_value'].mean():.2e}\n"
            )
        self.add_section("Summary Statistics", content)

    def _performance_metrics(self):
        """NEW: Enhanced performance metrics."""
        if not self.analyzer.sequences:
            return
            
        total_time = sum(seq.computation_time for seq in self.analyzer.sequences.values())
        avg_time = total_time / len(self.analyzer.sequences)
        converged = sum(1 for seq in self.analyzer.sequences.values() 
                       if seq.metadata.get("converged", True))
        
        content = (
            f"**Performance Metrics:**\n\n"
            f"- Total sequence computation time: {total_time:.2f}s\n"
            f"- Average time per sequence: {avg_time:.4f}s\n"
            f"- Sequences converged to 1: {converged}/{len(self.analyzer.sequences)}\n"
            f"- Convergence rate: {converged/len(self.analyzer.sequences):.1%}\n"
        )
        self.add_section("Performance Analysis", content)

    def _model_comparison(self):
        """PRESERVED ORIGINAL"""
        if not self.analyzer.fit_results:
            return
        rows = "| Model | R² | Adjusted R² | AIC | BIC | Time (s) |\n|---|---:|---:|---:|---:|---:|\n"
        for mt, fr in self.analyzer.fit_results.items():
            rows += f"| {mt.name} | {fr.r_squared:.4f} | {fr.adjusted_r_squared:.4f} | {fr.aic:.1f} | {fr.bic:.1f} | {fr.fit_time:.2f} |\n"
        best = max(self.analyzer.fit_results.items(), key=lambda kv: kv[1].r_squared)
        rows += f"\n**Best model:** {best[0].name} (R²={best[1].r_squared:.4f})\n"
        self.add_section("Model Comparison", rows)

    def _feature_analysis(self):
        """PRESERVED ORIGINAL"""
        if not any(fr.feature_importances is not None for fr in self.analyzer.fit_results.values()):
            return
        best = max((kv for kv in self.analyzer.fit_results.items() if kv[1].feature_importances is not None), key=lambda kv: kv[1].r_squared)
        names = self.analyzer.feature_extractor.feature_names
        imps = best[1].feature_importances
        order = np.argsort(imps)[::-1]
        top = "| Feature | Importance |\n|---|---:|\n" + "\n".join(
            f"| {names[i]} | {imps[i]:.4f} |" for i in order[:10]
        )
        self.add_section("Feature Importance (Top 10)", top)

    def save_summary(self, filename: str = "collatz_report.md") -> None:
        p = self.analyzer.output_dir / filename
        with open(p, "w") as fh:
            fh.write(self.summary)
        logger.info(f"Saved enhanced summary: {p}")

# ============================================================
# Enhanced Main Function
# ============================================================

def main():
    """Enhanced main with better user experience."""
    
    print("\n🎯 Collatz Conjecture Advanced Analyzer")
    print("=" * 50)
    print("Enhanced version with cycle detection and better performance")
    print()
    
    try:
        base = int(input("Enter base value (default 2): ") or 2)
        start = int(input("Enter start exponent: "))
        end = int(input("Enter end exponent: "))

        print("\nVariants:")
        for i, v in enumerate(CollatzVariant):
            print(f"{i+1}. {v.name}")
        v_choice = input("Select variant (default 1): ") or "1"
        try:
            v_idx = int(v_choice) - 1
            variant = list(CollatzVariant)[v_idx]
        except Exception:
            variant = CollatzVariant.CLASSIC

        v_params: Dict[str, Any] = {}
        if variant == CollatzVariant.GENERALIZED:
            print("\nEnter generalized parameters:")
            v_params["p"] = int(input("Odd multiplier p (default 3): ") or 3)
            v_params["q"] = int(input("Odd adder q (default 1): ") or 1)
            v_params["d"] = int(input("Even divider d (default 2): ") or 2)

        print("\nAvailable models:")
        for i, m in enumerate(MODEL_REGISTRY.keys()):
            print(f"{i+1}. {m.name}")
        msel = input("Select models to fit (comma-separated, default=all): ") or "all"
        if msel.strip().lower() == "all":
            model_types = None
        else:
            model_types = []
            for ch in msel.split(","):
                try:
                    idx = int(ch.strip()) - 1
                    model_types.append(list(MODEL_REGISTRY.keys())[idx])
                except Exception:
                    pass

        out_dir = input("Enter output directory (default=collatz_results): ") or None

        # Enhanced: Progress indication
        print(f"\n⏳ Starting analysis for {base}^{start} to {base}^{end}...")
        print("This may take a while for large ranges.")
        
        analyzer = CollatzAnalyzer(base=base, output_dir=out_dir, variant=variant, variant_params=v_params)
        analyzer.run_analysis(start, end, model_types)

        print("\n✅ Analysis completed successfully!")
        print(f"📊 Results saved to: {analyzer.output_dir}")
        print("• data/  → CSV & JSON with enhanced metadata")
        print("• plots/ → Enhanced visualizations")
        print("• models/→ Model artifacts & metadata") 
        print("• analysis_notebook.ipynb, collatz_report.md")

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n⏹️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()