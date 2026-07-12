"""
RiemannFalsifier
═══════════════════════════════════════════════════════════════════════════════
Directed near-miss search for the Riemann Hypothesis using two independent
signal sources from the existing ReimannX modules:

Strategy 1 — zero_deviation_scan
    Computes non-trivial zeros ζ(ρ_n) = 0 via mpmath.zetazero() and scores
    each by |Re(ρ_n) − ½|.  Any positive score at working precision would be
    a counterexample.  Also measures spacing anomalies vs the GUE prediction
    (Montgomery's pair-correlation conjecture) as a secondary signal.

Strategy 2 — keiper_li_coefficients
    Computes the first N Keiper-Li coefficients λ_n.  Under RH all λ_n > 0
    and the sequence is eventually increasing.  A negative coefficient is a
    confirmed RH counterexample; a near-zero or decreasing coefficient is a
    high-value near-miss.

Near-miss scores are normalized to [0, 1] and compatible with the shared
FalsificationLedger so results can be merged and correlated with Collatz and
Goldbach runs via CrossEngineAnalysis.
"""

from __future__ import annotations

import logging
import math
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from codebase.FalsificationEngine.FalsificationEngine import FalsificationLedger, LedgerEntry

logger = logging.getLogger("proofx.riemann_falsifier")

# Working precision for mpmath computations.
# 30 dps gives deviations resolvable to ~1e-15; increase for tighter bounds.
_DEFAULT_PRECISION_DPS: int = 30

# Maximum Keiper-Li coefficients per run (each is expensive: ~O(n²) mpmath ops).
_MAX_KEIPER_LI: int = 20


class RiemannFalsifier:
    """Near-miss search for counterexamples to the Riemann Hypothesis.

    Usage
    ─────
        rf = RiemannFalsifier()
        ledger = rf.search(budget=60, seed=0)
        # budget splits: half zeros, half Keiper-Li (capped at _MAX_KEIPER_LI)
    """

    def __init__(self, precision_dps: int = _DEFAULT_PRECISION_DPS) -> None:
        try:
            import mpmath

            self._mp = mpmath
        except ImportError as exc:
            raise RuntimeError(
                "mpmath is required for RiemannFalsifier - pip install mpmath"
            ) from exc
        self._precision_dps = precision_dps
        self._mp.mp.dps = precision_dps
        # Below this deviation, the score is effectively 0 (within precision floor).
        self._dev_floor = 10.0 ** (-(precision_dps // 2))

    # ── Public entry point ────────────────────────────────────────────────────

    def search(self, budget: int, seed: int) -> FalsificationLedger:
        """Run both strategies and return a combined ledger.

        Budget is split: half to zero-deviation scan, the remainder (up to
        _MAX_KEIPER_LI) to Keiper-Li coefficient analysis.
        """
        ledger = FalsificationLedger()
        half = max(1, budget // 2)
        kl_budget = min(_MAX_KEIPER_LI, budget - half)

        logger.info(
            "RiemannFalsifier start: %d zeros + %d Keiper-Li coefficients",
            half,
            kl_budget,
        )

        self._zero_deviation_scan(half, seed, ledger)
        if kl_budget > 0:
            self._keiper_li_scan(kl_budget, seed, ledger)

        logger.info(
            "RiemannFalsifier complete: %d ledger entries | top near-miss: %.4f",
            len(ledger),
            ledger.top_k(1)[0].near_miss_score if ledger else 0.0,
        )
        return ledger

    # ── Strategy 1: zero-deviation scan ──────────────────────────────────────

    def _zero_deviation_scan(self, n_zeros: int, seed: int, ledger: FalsificationLedger) -> None:
        """Compute the first n_zeros non-trivial zeros and score by deviation."""
        mp = self._mp
        mp.mp.dps = self._precision_dps

        prev_imag: float | None = None
        evaluated = 0

        for idx in range(1, n_zeros + 1):
            t0 = time.perf_counter()
            try:
                zero = mp.zetazero(idx)
                z = complex(zero)
            except Exception as exc:
                logger.debug("zetazero(%d) failed: %s", idx, exc)
                continue
            elapsed = time.perf_counter() - t0

            deviation = abs(z.real - 0.5)
            # Score rises smoothly from 0 as deviation exceeds the precision floor.
            # tanh maps [0, ∞) → [0, 1) with saturation near the confirmed limit.
            dev_score = math.tanh(deviation / max(self._dev_floor, 1e-30))

            # Spacing anomaly vs GUE prediction.
            T = abs(z.imag)
            # Mean spacing near height T from Riemann–von Mangoldt: 2π/log(T/2π)
            mean_spacing = 2.0 * math.pi / math.log(max(T / (2.0 * math.pi), 1.1))
            if prev_imag is not None:
                spacing = T - prev_imag
                norm_s = spacing / mean_spacing
                # Distance from 1.0 (the GUE mean), saturated at 3σ
                spacing_anomaly = min(1.0, abs(norm_s - 1.0) / 3.0)
            else:
                norm_s = 1.0
                spacing_anomaly = 0.0

            near_miss = min(1.0, 0.70 * dev_score + 0.30 * spacing_anomaly)

            if near_miss >= 1.0:
                logger.critical(
                    "RIEMANN OFF-LINE ZERO: ρ_%d = (%.15f + %.15fi)  deviation=%.3e",
                    idx,
                    z.real,
                    z.imag,
                    deviation,
                )

            ledger.append(
                LedgerEntry(
                    candidate=idx,
                    conjecture="riemann",
                    strategy="zero_deviation_scan",
                    features={
                        "imaginary_part": round(z.imag, 6),
                        "real_deviation": deviation,
                        "normalized_spacing": round(norm_s, 6),
                        "spacing_anomaly": round(spacing_anomaly, 6),
                        "dev_score": round(dev_score, 6),
                    },
                    near_miss_score=round(near_miss, 6),
                    details={
                        "zero_index": idx,
                        "zero_real": z.real,
                        "zero_imag": z.imag,
                        "deviation_from_half": deviation,
                        "mean_spacing": round(mean_spacing, 6),
                        "precision_dps": self._precision_dps,
                        "computation_time_s": round(elapsed, 4),
                    },
                    timestamp=time.time(),
                    rng_seed=seed,
                )
            )
            prev_imag = z.imag
            evaluated += 1

            if evaluated % 10 == 0:
                logger.info(
                    "RH zero scan: %d/%d | max deviation %.2e",
                    evaluated,
                    n_zeros,
                    deviation,
                )

    # ── Strategy 2: Keiper-Li coefficient analysis ────────────────────────────

    def _keiper_li_scan(self, n_coeffs: int, seed: int, ledger: FalsificationLedger) -> None:
        """Compute Keiper-Li λ_n and score violations of positivity/monotonicity."""
        mp = self._mp
        mp.mp.dps = self._precision_dps

        def xi(s: Any) -> Any:
            # Completed Riemann xi function: ξ(s) = ½·s(s-1)·π^{-s/2}·Γ(s/2)·ζ(s)
            return 0.5 * s * (s - 1) * mp.gamma(s / 2) * mp.power(mp.pi, -s / 2) * mp.zeta(s)

        prev_lambda: float | None = None

        for n in range(1, n_coeffs + 1):
            t0 = time.perf_counter()
            try:
                # λ_n = (1/(n-1)!) · d^n/ds^n [ s^{n-1} · log ξ(s) ] |_{s=1}
                def f(s: Any, _n: int = n) -> Any:
                    return mp.power(s, _n - 1) * mp.log(xi(s))

                deriv = mp.diff(f, 1, n)
                lambda_n = float(deriv / mp.factorial(n - 1))
            except Exception as exc:
                logger.debug("Keiper-Li λ_%d failed: %s", n, exc)
                continue
            elapsed = time.perf_counter() - t0

            # Positivity score: RH requires λ_n > 0 for all n.
            if lambda_n <= 0.0:
                positivity_score = 1.0
                logger.critical(
                    "KEIPER-LI VIOLATION: λ_%d = %.8f  (non-positive — RH counterexample candidate)",
                    n,
                    lambda_n,
                )
            else:
                # Expected asymptotic: λ_n ~ ½·n·log(n)
                expected = 0.5 * n * math.log(max(n, 2))
                # Score rises as λ_n shrinks toward 0 relative to expectation.
                ratio = lambda_n / max(expected, 1e-30)
                positivity_score = math.tanh(max(0.0, 1.0 - ratio))

            # Monotonicity score: λ_n should increase (soft condition).
            if prev_lambda is not None and lambda_n < prev_lambda:
                drop = prev_lambda - lambda_n
                monotone_score = min(1.0, drop / max(abs(prev_lambda), 1e-9))
            else:
                monotone_score = 0.0

            near_miss = min(1.0, 0.75 * positivity_score + 0.25 * monotone_score)

            ledger.append(
                LedgerEntry(
                    candidate=n,
                    conjecture="riemann",
                    strategy="keiper_li_coefficients",
                    features={
                        "lambda_n": round(lambda_n, 8),
                        "lambda_prev": round(prev_lambda, 8) if prev_lambda is not None else 0.0,
                        "positivity_score": round(positivity_score, 6),
                        "monotone_score": round(monotone_score, 6),
                    },
                    near_miss_score=round(near_miss, 6),
                    details={
                        "n": n,
                        "lambda_n": lambda_n,
                        "is_positive": lambda_n > 0.0,
                        "is_increasing": prev_lambda is None or lambda_n > prev_lambda,
                        "precision_dps": self._precision_dps,
                        "computation_time_s": round(elapsed, 4),
                    },
                    timestamp=time.time(),
                    rng_seed=seed,
                )
            )
            prev_lambda = lambda_n

            logger.info(
                "Keiper-Li λ_%d = %.8f | near_miss=%.4f | elapsed=%.2fs",
                n,
                lambda_n,
                near_miss,
                elapsed,
            )
