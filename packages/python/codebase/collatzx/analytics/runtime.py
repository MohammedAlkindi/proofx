"""Runtime configuration and logging for the Collatz analytics package."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None  # type: ignore[assignment]


class EnhancedConfig:
    """Configuration shared by Collatz sequence and model computations."""

    def __init__(self) -> None:
        self.MAX_ITERATIONS = 10_000_000
        self.MAX_VALUE = 10**100
        self.DEFAULT_OUTPUT_DIR = Path("collatz_results")
        self.CACHE_DIR = Path(".collatz_cache")
        self.PLOT_STYLE = "seaborn-v0_8-darkgrid"

        self.USE_GPU = torch is not None and torch.cuda.is_available()
        self.MAX_PROCESSES = max(1, (__import__("os").cpu_count() or 2) - 1)
        self.PRECISION = np.float64
        self.ENABLE_CACHE = True
        self.ENABLE_PROGRESS_BAR = True
        self.DEFAULT_TEST_SIZE = 0.2
        self.RANDOM_SEED = 42
        self.EARLY_STOPPING_PATIENCE = 5

        self.RF_N_EST = [100, 200]
        self.RF_MAX_DEPTH = [None, 10, 20]
        self.RF_MIN_SAMPLES_SPLIT = [2, 5]
        self.NN_HIDDEN_LAYERS = [(100, 50), (64, 32)]

        self.CACHE_MAX_SIZE = 100000
        self.CHUNK_SIZE = 1000
        self.ENABLE_CYCLE_DETECTION = True

        self._setup_determinism()

    def _setup_determinism(self) -> None:
        """Configure the legacy deterministic defaults used by the analyzer."""
        np.random.seed(self.RANDOM_SEED)
        if torch is not None:
            torch.manual_seed(self.RANDOM_SEED)
            if torch.cuda.is_available():
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False


config = EnhancedConfig()
logger = logging.getLogger("collatz")
logger.addHandler(logging.NullHandler())


class EnhancedFormatter(logging.Formatter):
    """Formatter retained for compatibility with the original analyzer."""


def configure_logging(log_dir: Path = Path(".logs")) -> None:
    """Configure console and rotating file logging for command-line runs."""
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                log_dir / "collatz_debug.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            ),
            logging.FileHandler(log_dir / "collatz_analysis.log"),
        ],
        force=True,
    )
