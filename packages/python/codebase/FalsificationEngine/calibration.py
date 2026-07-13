"""
Score Calibration for FalsificationEngine
══════════════════════════════════════════
Converts raw near-miss scores (heuristic composites in [0,1]) into
interpretable probability estimates P(counterexample | score).

Two calibration methods are provided:

  IsotonicCalibrator — sklearn's IsotonicRegression constrained to be
      monotone non-decreasing.  Fits perfectly to any arbitrary score
      distribution without parametric assumptions.  Preferred when you
      have ≥ 100 ledger entries.

  PlattCalibrator — logistic regression (Platt scaling) on the raw scores.
      Assumes a sigmoid relationship between score and probability.  More
      stable with small ledgers (<100 entries) but less flexible.

Workflow
────────
1. Run FalsificationEngine for a long budget to accumulate a ledger.
2. Manually label a subset of entries as "true near-misses" (y=1) or
   "routine" (y=0).  In practice, entries with stopping_time anomalies
   confirmed by an independent verifier are labeled 1.
3. Fit a calibrator:
       cal = IsotonicCalibrator()
       cal.fit(scores, labels)
       cal.save("calibrator.pkl")
4. Apply to new search output:
       probs = cal.predict(new_scores)
5. Attach back to ledger entries for human-readable confidence display.

Reproducibility
───────────────
fit() accepts a seed for the cross-validation split so calibrated
probability estimates are reproducible across machines.
"""

from __future__ import annotations

import json
import logging
import math
import pickle
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("proofx.calibration")

# ── Calibration result ────────────────────────────────────────────────────────


@dataclass
class CalibrationReport:
    """Summary of a calibration fit."""

    method: str
    n_samples: int
    brier_score: float  # lower is better; 0 = perfect, 0.25 = coin-flip baseline
    log_loss: float  # lower is better
    expected_calibration_error: float  # ECE across 10 equal-width bins
    score_min: float
    score_max: float
    seed: int

    def to_dict(self):
        return asdict(self)

    def summary(self) -> str:
        return (
            f"[{self.method}] n={self.n_samples} | "
            f"Brier={self.brier_score:.4f} | LogLoss={self.log_loss:.4f} | "
            f"ECE={self.expected_calibration_error:.4f}"
        )


# ── Base class ────────────────────────────────────────────────────────────────


class _BaseCalibrator:
    def fit(
        self, scores: Sequence[float], labels: Sequence[int], seed: int = 0
    ) -> CalibrationReport:
        raise NotImplementedError

    def predict(self, scores: Sequence[float]) -> np.ndarray:
        raise NotImplementedError

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(self, fh)
        logger.info("Calibrator saved: %s", path)

    @staticmethod
    def load(path: Path) -> _BaseCalibrator:
        with open(path, "rb") as fh:
            obj = pickle.load(fh)
        if not isinstance(obj, _BaseCalibrator):
            raise TypeError(f"Expected _BaseCalibrator payload in {path}")
        logger.info("Calibrator loaded: %s", path)
        return obj

    # ── Shared metrics ────────────────────────────────────────────────────────

    @staticmethod
    def _brier(probs: np.ndarray, labels: np.ndarray) -> float:
        return float(np.mean((probs - labels) ** 2))

    @staticmethod
    def _log_loss(probs: np.ndarray, labels: np.ndarray, eps: float = 1e-7) -> float:
        p = np.clip(probs, eps, 1 - eps)
        return float(-np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p)))

    @staticmethod
    def _ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        """Expected Calibration Error across equal-width bins."""
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        for lo, hi in zip(bins[:-1], bins[1:], strict=False):
            mask = (probs >= lo) & (probs < hi)
            if mask.sum() == 0:
                continue
            acc = labels[mask].mean()
            conf = probs[mask].mean()
            ece += mask.mean() * abs(acc - conf)
        return float(ece)

    def _report(
        self,
        method: str,
        scores: np.ndarray,
        labels: np.ndarray,
        probs: np.ndarray,
        seed: int,
    ) -> CalibrationReport:
        return CalibrationReport(
            method=method,
            n_samples=len(scores),
            brier_score=self._brier(probs, labels),
            log_loss=self._log_loss(probs, labels),
            expected_calibration_error=self._ece(probs, labels),
            score_min=float(scores.min()),
            score_max=float(scores.max()),
            seed=seed,
        )


# ── Isotonic calibrator ───────────────────────────────────────────────────────


class IsotonicCalibrator(_BaseCalibrator):
    """Monotone non-decreasing calibration via IsotonicRegression.

    Preferred for ≥ 100 labelled entries.  Makes no parametric assumption
    about the score→probability mapping beyond monotonicity, which is a
    physically reasonable constraint: a higher near-miss score should never
    correspond to a lower counterexample probability.
    """

    def __init__(self) -> None:
        self._model: Any = None

    def fit(
        self, scores: Sequence[float], labels: Sequence[int], seed: int = 0
    ) -> CalibrationReport:
        try:
            from sklearn.isotonic import IsotonicRegression
        except ImportError as e:
            raise ImportError("scikit-learn is required for IsotonicCalibrator") from e

        X = np.asarray(scores, dtype=float)
        y = np.asarray(labels, dtype=float)

        if len(X) < 10:
            raise ValueError(f"Need at least 10 labelled entries; got {len(X)}")
        if not np.all((y == 0) | (y == 1)):
            raise ValueError("Labels must be binary (0 or 1)")

        self._model = IsotonicRegression(out_of_bounds="clip")
        self._model.fit(X, y)
        probs = self._model.predict(X)

        report = self._report("isotonic", X, y, probs, seed)
        logger.info("IsotonicCalibrator fit: %s", report.summary())
        return report

    def predict(self, scores: Sequence[float]) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Call fit() before predict()")
        return np.asarray(self._model.predict(np.asarray(scores, dtype=float)), dtype=float)


# ── Platt (logistic) calibrator ───────────────────────────────────────────────


class PlattCalibrator(_BaseCalibrator):
    """Sigmoid (logistic) calibration — Platt scaling.

    More stable than isotonic with small samples (<100 entries) because it
    has only two parameters (A, B in the sigmoid A·score + B).

    The sigmoid is fitted by minimising cross-entropy via L-BFGS-B.
    """

    def __init__(self) -> None:
        self._A: float | None = None
        self._B: float | None = None

    def fit(
        self, scores: Sequence[float], labels: Sequence[int], seed: int = 0
    ) -> CalibrationReport:
        try:
            from scipy.optimize import minimize
        except ImportError as e:
            raise ImportError("scipy is required for PlattCalibrator") from e

        X = np.asarray(scores, dtype=float)
        y = np.asarray(labels, dtype=float)

        if not np.all((y == 0) | (y == 1)):
            raise ValueError("Labels must be binary (0 or 1)")

        # Platt's prior-corrected targets to avoid over-fitting on edges
        n_pos = y.sum()
        n_neg = len(y) - n_pos
        t_pos = (n_pos + 1) / (n_pos + 2)
        t_neg = 1 / (n_neg + 2)
        t = np.where(y == 1, t_pos, t_neg)

        def neg_log_likelihood(params):
            A, B = params
            f = A * X + B
            p = 1.0 / (1.0 + np.exp(-np.clip(f, -500, 500)))
            return -np.mean(t * np.log(p + 1e-9) + (1 - t) * np.log(1 - p + 1e-9))

        result = minimize(
            neg_log_likelihood, x0=[0.0, math.log((n_neg + 1) / (n_pos + 1))], method="L-BFGS-B"
        )
        self._A, self._B = float(result.x[0]), float(result.x[1])

        probs = self.predict(X.tolist())
        report = self._report("platt", X, y, probs, seed)
        logger.info("PlattCalibrator fit: A=%.4f B=%.4f | %s", self._A, self._B, report.summary())
        return report

    def predict(self, scores: Sequence[float]) -> np.ndarray:
        if self._A is None or self._B is None:
            raise RuntimeError("Call fit() before predict()")
        a = self._A
        b = self._B
        f = a * np.asarray(scores, dtype=float) + b
        return 1.0 / (1.0 + np.exp(-np.clip(f, -500, 500)))


# ── Attach calibrated probabilities to a ledger ───────────────────────────────


def annotate_ledger(
    ledger_path: Path, calibrator: _BaseCalibrator, output_path: Path | None = None
) -> None:
    """Read a JSONL ledger, attach calibrated_prob to each entry, write output.

    If output_path is None, writes to ledger_path with a .calibrated.jsonl suffix.
    """
    ledger_path = Path(ledger_path)
    output_path = output_path or ledger_path.with_suffix(".calibrated.jsonl")

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    if not entries:
        logger.warning("Empty ledger at %s", ledger_path)
        return

    scores = [e["near_miss_score"] for e in entries]
    probs = calibrator.predict(scores)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        for entry, prob in zip(entries, probs, strict=False):
            entry["calibrated_prob"] = round(float(prob), 6)
            fh.write(json.dumps(entry) + "\n")

    logger.info("Annotated %d entries → %s", len(entries), output_path)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Calibrate ProofX near-miss scores to probability estimates"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # fit subcommand
    fit_p = sub.add_parser("fit", help="Fit a calibrator from a labelled JSONL file")
    fit_p.add_argument(
        "--ledger",
        required=True,
        help="JSONL ledger (each entry must have near_miss_score and label fields)",
    )
    fit_p.add_argument("--method", choices=["isotonic", "platt"], default="isotonic")
    fit_p.add_argument(
        "--output", default="calibrator.pkl", help="Where to save the fitted calibrator"
    )
    fit_p.add_argument("--seed", type=int, default=0)

    # annotate subcommand
    ann_p = sub.add_parser("annotate", help="Add calibrated_prob to an existing ledger")
    ann_p.add_argument("--ledger", required=True, help="Input JSONL ledger")
    ann_p.add_argument("--calibrator", required=True, help="Path to fitted .pkl calibrator")
    ann_p.add_argument("--output", default=None, help="Output path (default: .calibrated.jsonl)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    if args.cmd == "fit":
        lines = Path(args.ledger).read_text(encoding="utf-8").splitlines()
        entries = [json.loads(line) for line in lines if line.strip()]
        if not entries:
            parser.error("Ledger is empty")
        if "label" not in entries[0]:
            parser.error(
                "Each entry must have a 'label' field (0 or 1). Add labels manually before fitting."
            )

        scores = [e["near_miss_score"] for e in entries]
        labels = [int(e["label"]) for e in entries]

        cal: _BaseCalibrator = (
            IsotonicCalibrator() if args.method == "isotonic" else PlattCalibrator()
        )
        report = cal.fit(scores, labels, seed=args.seed)
        print(report.summary())
        cal.save(Path(args.output))

    elif args.cmd == "annotate":
        cal = _BaseCalibrator.load(Path(args.calibrator))
        out = Path(args.output) if args.output else None
        annotate_ledger(Path(args.ledger), cal, out)


if __name__ == "__main__":
    main()
