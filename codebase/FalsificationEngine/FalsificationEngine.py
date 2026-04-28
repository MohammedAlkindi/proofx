"""
FalsificationEngine
═══════════════════════════════════════════════════════════════════════════════
Directed counterexample search for the Collatz and Goldbach conjectures.

Design philosophy
─────────────────
Uniform (brute-force) scanning wastes compute on numbers that trivially satisfy
each conjecture.  This engine applies two principled strategies:

  Collatz  — Inverse-tree beam search.  We expand backward from seeds with
             known anomalous stopping times, following the exact inverse Collatz
             map.  Any number that reaches a dangerous seed inherits its risky
             suffix; the feature vector from Analytics.py quantifies that risk
             as a continuous score.

  Goldbach — Hardy-Littlewood deficit search.  Conjecture B (H-L) predicts the
             expected partition count G(n).  We search even numbers whose actual
             G(n) falls furthest below that prediction — the numbers structurally
             closest to having NO partition (i.e., a counterexample).

Reproducibility guarantee: all randomness flows through a single seeded
np.random.Generator; given seed s, the search path is identical across runs.
"""

from __future__ import annotations

import contextlib
import concurrent.futures
import heapq
import io
import json
import logging
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import numpy as np

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proofx.falsification")

# ── Resolve ProofX root so intra-codebase imports work regardless of CWD ─────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from codebase.CollatzX.Analytics.Analytics import (
    AlgebraicFeatureExtractor,
    CollatzSequence,
    FeatureUnion,
    StatisticalFeatureExtractor,
)
from codebase.GoldbachX.AlgebraicExtensions.AlgebraicExtensions import (
    composite_precheck,
    mod_class_prune,
)
from codebase.GoldbachX.SieveEngine.SieveEngine import eratosthenes

# ── Mathematical constants ────────────────────────────────────────────────────

# Hardy-Littlewood twin-prime constant C₂ = ∏_{p≥3} p(p-2)/(p-1)²
# Converges slowly; this 10-decimal approximation is sufficient for scoring.
_C2: float = 0.6601618158

# Parity threshold: convergence requires parity_ratio < log₂(3) - 1 = log(2)/log(3)
# Derivation: each odd step multiplies by ~3 and each even step by 1/2.
# For the long-run product to tend toward 0 we need k_odd·log3 < k_total·log2,
# i.e., parity_ratio < log(2)/log(3) ≈ 0.6309.
_PARITY_CONVERGENCE_THRESHOLD: float = math.log(2) / math.log(3)

# Stopping-time "normal" scale: empirically, most n converge in ≈ 2·log₂(n) steps.
# We use this to normalise the excursion contribution to the near-miss score.
_EXPECTED_ST_SCALE: float = 2.0

# Known Collatz champions (seeds with stopping times far above expectation).
# Source: Oliveira e Silva's exhaustive verification tables.
# Using these as beam-search anchors focuses the budget on the most anomalous region.
_COLLATZ_ANCHORS: List[int] = [27, 703, 871, 6171, 77031, 837799, 8400511, 63728127]

# Sieve limit for Goldbach partition computation.
_SIEVE_LIMIT: int = 200_000

# ── Shared data structures ────────────────────────────────────────────────────


@dataclass
class LedgerEntry:
    """Immutable record of one falsification test.

    Every field is included so that the ledger alone is sufficient to reproduce
    the search decision that produced this candidate.
    """

    candidate: int
    conjecture: str             # "collatz" | "goldbach"
    strategy: str               # search strategy name that produced this candidate
    features: Dict[str, float]  # full feature vector at test time
    near_miss_score: float      # ∈ [0, 1]; 1 = confirmed counterexample
    details: Dict[str, Any]     # conjecture-specific diagnostics
    timestamp: float            # epoch seconds
    rng_seed: int               # seed in effect when generated (for full replay)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FalsificationLedger:
    """Append-only structured record of all falsification attempts.

    Maintains an internal max-heap over near_miss_score so that top-k queries
    are O(k·log n) rather than O(n·log n).
    """

    def __init__(self) -> None:
        self._entries: List[LedgerEntry] = []
        # Heap stores (−near_miss_score, index) so heappop gives the highest score.
        self._heap: List[Tuple[float, int]] = []

    def append(self, entry: LedgerEntry) -> None:
        idx = len(self._entries)
        self._entries.append(entry)
        heapq.heappush(self._heap, (-entry.near_miss_score, idx))

    def top_k(self, k: int) -> List[LedgerEntry]:
        """Return the k entries with the highest near-miss score."""
        heap_copy = list(self._heap)
        result: List[LedgerEntry] = []
        while heap_copy and len(result) < k:
            _, idx = heapq.heappop(heap_copy)
            result.append(self._entries[idx])
        return result

    def __len__(self) -> int:
        return len(self._entries)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e.to_dict()) for e in self._entries)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_jsonl())
        logger.info("Ledger saved: %s (%d entries)", path, len(self))


# ── Collatz Falsifier ─────────────────────────────────────────────────────────


class CollatzFalsifier:
    """Directed search for Collatz counterexample candidates.

    Algorithm
    ─────────
    1. Seed the priority queue with _COLLATZ_ANCHORS (known champion stopping times).
    2. Pop the highest-risk candidate from the queue.
    3. Compute its full feature vector (via Analytics.py FeatureUnion) and
       near-miss score.
    4. Record to ledger.
    5. Expand the candidate via:
       (a) Inverse Collatz map: predecessors that map TO this candidate in one step.
       (b) Residue-class neighborhood: numbers sharing the same (n mod 6) class,
           shifted by powers of 2, which preserves the parity structure.
    6. Add unexplored successors whose quick-score exceeds a threshold to the queue.
    7. Repeat until budget exhausted.

    Why inverse-tree, not forward scan?
    The inverse Collatz tree rooted at any champion seed clusters ALL numbers that
    visit that seed's risky trajectory.  Expanding backward concentrates the budget
    on this cluster rather than uniformly sampling ℕ.
    """

    # Feature weights for the risk score.
    # Mathematical justification for each:
    #   lyapunov  0.35 — average log-expansion rate; positive ⟹ sequence diverging locally
    #   hurst     0.25 — H > 0.5 means persistent trending; a number "in the groove" of growth
    #   parity    0.20 — excess odd-step fraction above the convergence threshold (0.6309)
    #   binary    0.10 — high entropy ⟹ complex bit pattern, resists fast-path convergence
    #   growth    0.10 — normalized mean ascent per step
    _RISK_WEIGHTS: Dict[str, float] = {
        "lyapunov_exponent": 0.35,
        "hurst_exponent": 0.25,
        "parity_excess": 0.20,
        "binary_entropy": 0.10,
        "growth_rate": 0.10,
    }
    assert abs(sum(_RISK_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1"

    # Only expand predecessors within this factor of the current candidate.
    # Prevents unbounded growth via the 2n doubling chain.
    _MAX_PREDECESSOR_RATIO: float = 4.0

    # Minimum quick-score to add a neighbor to the queue (avoids queue bloat).
    _QUEUE_ADMIT_THRESHOLD: float = 0.05

    def __init__(self) -> None:
        self._extractor = FeatureUnion([StatisticalFeatureExtractor(), AlgebraicFeatureExtractor()])

    # ── Core mathematics ─────────────────────────────────────────────────────

    def _risk_score(self, features: Dict[str, float]) -> float:
        """Continuous risk score ∈ [0, 1] from a feature vector.

        Each feature is clipped and normalized to [0, 1] before weighting:
          lyapunov  : max(0, raw_value); negative ⟹ no risk contribution
          hurst     : max(0, H - 0.5) * 2  maps [0.5, 1.0] → [0, 1]
          parity    : max(0, ratio - threshold) / (1 - threshold)
          binary    : raw_value / log2(seq_len), already ∈ [0, 1] approximately
          growth    : abs(rate) clipped to [0, 1]
        """
        lyapunov = max(0.0, features.get("lyapunov_exponent", 0.0))
        hurst = max(0.0, (features.get("hurst_exponent", 0.5) - 0.5) * 2.0)
        parity_raw = features.get("parity_ratio", 0.0)
        parity_excess = max(0.0, (parity_raw - _PARITY_CONVERGENCE_THRESHOLD) /
                            (1.0 - _PARITY_CONVERGENCE_THRESHOLD))
        binary_ent = min(1.0, max(0.0, features.get("binary_entropy", 0.0)))
        growth = min(1.0, abs(features.get("growth_rate", 0.0)))

        normalized = {
            "lyapunov_exponent": min(1.0, lyapunov),
            "hurst_exponent": min(1.0, hurst),
            "parity_excess": min(1.0, parity_excess),
            "binary_entropy": binary_ent,
            "growth_rate": growth,
        }
        return sum(self._RISK_WEIGHTS[k] * normalized[k] for k in self._RISK_WEIGHTS)

    def _near_miss_score(
        self, seed: int, features: Dict[str, float], stopping_time: int, max_value: int
    ) -> float:
        """Near-miss score for a Collatz candidate.

        Components:
          risk_component   : the feature-based risk score (already ∈ [0,1])
          excursion_bonus  : normalized log-ratio of max_value / seed — a sequence
                             that climbs to 1000× its starting value is closer to
                             one that never descends.  Normalised by the expected
                             stopping time scale to keep ∈ [0, 1].

        Final score = 0.7 * risk + 0.3 * excursion_bonus
        """
        risk = self._risk_score(features)
        if seed > 0 and stopping_time > 0:
            # Expected stopping time ≈ _EXPECTED_ST_SCALE * log₂(seed)
            expected_st = _EXPECTED_ST_SCALE * math.log2(max(seed, 2))
            excursion = math.log1p(max_value / max(seed, 1))
            # Normalise: a sequence with 5× its expected stopping time gets full credit
            excursion_norm = min(1.0, excursion / (math.log(5.0) * expected_st / stopping_time))
        else:
            excursion_norm = 0.0

        return 0.7 * risk + 0.3 * excursion_norm

    @staticmethod
    def _inverse_collatz_predecessors(n: int) -> List[int]:
        """All integers that map to n in exactly one Collatz step.

        Two cases:
          (1) 2n   — always a predecessor, since 2n is even and 2n/2 = n.
          (2) (n-1)/3 — predecessor via the odd rule: if m is odd and 3m+1 = n,
              then m = (n-1)/3.  This requires n ≡ 1 (mod 3) and (n-1)/3 odd and > 1.

        We do NOT return 2n unconditionally in the beam search; doubling just
        prepends an even step, which adds no structural risk information beyond
        what n already contains.  We keep 2n only if n itself is already high-risk
        and the doubled predecessor is within _MAX_PREDECESSOR_RATIO of n.
        """
        preds: List[int] = []

        # Odd-rule inverse: 3m + 1 = n  ⟹  m = (n-1)/3
        k = n - 1
        if k > 0 and k % 3 == 0:
            m = k // 3
            # m must be odd (otherwise the odd rule would not have been applied)
            if m > 1 and m % 2 == 1:
                preds.append(m)

        # Even-rule inverse: 2n/2 = n, so 2n maps to n.
        # Include only if manageable — prevents infinite doubling chains.
        preds.append(2 * n)

        return preds

    @staticmethod
    def _residue_neighborhood(n: int, rng: np.random.Generator, width: int = 8) -> List[int]:
        """Numbers near n that share its residue class mod 6.

        The Collatz structure is strongly influenced by n mod 6:
          n ≡ 1 (mod 6) → always reaches n ≡ 4 (mod 6) in one odd step (3n+1 ≡ 4 mod 6)
          n ≡ 3 (mod 6) → reaches n ≡ 10 ≡ 4 (mod 6) (3n+1=10k)
          n ≡ 5 (mod 6) → reaches n ≡ 16 ≡ 4 (mod 6) (3n+1=16k)
        Searching within the same residue class mod 6 preserves this structural
        property while exploring a different scale.
        """
        residue = n % 6
        offsets = rng.choice(
            [2**k for k in range(1, 7)], size=min(width, 6), replace=False
        )
        neighbors = []
        for off in offsets:
            # Adjust offset to preserve residue class
            candidate = n + off
            while candidate % 6 != residue:
                candidate += 1
            if candidate > 1:
                neighbors.append(candidate)
        return neighbors

    # ── Quick-score for queue admission ──────────────────────────────────────

    @staticmethod
    def _quick_score(n: int) -> float:
        """Cheap proxy score for queue admission, O(log n) time.

        Uses bit-level statistics as cheap feature proxies:
          - odd_density: fraction of 1-bits (proxy for parity_ratio)
          - bit_entropy: Shannon entropy of the bit string (proxy for binary_entropy)

        Both are computable without running the full Collatz sequence.
        """
        bits = bin(n)[2:]
        ones = bits.count("1")
        total = len(bits)
        p = ones / total
        q_ = 1.0 - p
        # Shannon entropy of Bernoulli(p) on the bit string
        ent = 0.0
        if p > 0:
            ent -= p * math.log2(p)
        if q_ > 0:
            ent -= q_ * math.log2(q_)
        # odd_density > convergence threshold contributes positive score
        parity_contrib = max(0.0, p - _PARITY_CONVERGENCE_THRESHOLD)
        return 0.5 * min(1.0, parity_contrib / 0.2) + 0.5 * ent

    # How often (in evaluations) to re-seed the queue from the current top-k.
    _ANCHOR_REFRESH_INTERVAL: int = 50
    # Number of top ledger entries to recycle as new anchors on each refresh.
    _ANCHOR_REFRESH_TOP_K: int = 5

    # ── Beam search ──────────────────────────────────────────────────────────

    def search(self, budget: int, seed: int) -> FalsificationLedger:
        """Run the inverse-tree beam search with dynamic anchor refresh.

        Parameters
        ──────────
        budget : number of candidates to fully evaluate (each requires computing
                 the Collatz sequence and full feature vector)
        seed   : RNG seed for reproducibility

        Returns
        ───────
        FalsificationLedger populated with `budget` entries, ordered internally
        by near-miss score.
        """
        rng = np.random.default_rng(seed)
        ledger = FalsificationLedger()
        visited: Set[int] = set()

        # Priority queue: (−quick_score, candidate).
        # Negated so heapq (min-heap) acts as a max-heap over quick_score.
        pq: List[Tuple[float, int]] = []
        for anchor in _COLLATZ_ANCHORS:
            heapq.heappush(pq, (-self._quick_score(anchor), anchor))

        evaluated = 0
        while pq and evaluated < budget:
            _, candidate = heapq.heappop(pq)

            if candidate in visited or candidate < 2:
                continue
            visited.add(candidate)

            entry = self._evaluate(candidate, seed, rng)
            if entry is None:
                continue
            ledger.append(entry)
            evaluated += 1

            if evaluated % self._ANCHOR_REFRESH_INTERVAL == 0:
                logger.info(
                    "Collatz search: %d/%d evaluated | top near-miss: %.4f",
                    evaluated,
                    budget,
                    ledger.top_k(1)[0].near_miss_score if ledger else 0.0,
                )
                # Dynamic anchor refresh: re-seed queue from current top-k so
                # the search keeps expanding around the highest-risk region found
                # so far rather than drifting away from it via the doubling chain.
                for refresh_entry in ledger.top_k(self._ANCHOR_REFRESH_TOP_K):
                    anchor = refresh_entry.candidate
                    if anchor not in visited:
                        heapq.heappush(pq, (-self._quick_score(anchor), anchor))

            # Expand: predecessors + residue neighborhood
            predecessors = self._inverse_collatz_predecessors(candidate)
            neighbors = self._residue_neighborhood(candidate, rng)

            for nbr in predecessors + neighbors:
                if nbr in visited or nbr < 2:
                    continue
                # Only admit to queue if quick-score above threshold
                qs = self._quick_score(nbr)
                if qs >= self._QUEUE_ADMIT_THRESHOLD:
                    heapq.heappush(pq, (-qs, nbr))

        logger.info(
            "Collatz search complete: %d candidates evaluated, %d in queue",
            evaluated,
            len(pq),
        )
        return ledger

    def _evaluate(
        self, candidate: int, base_seed: int, rng: np.random.Generator
    ) -> Optional[LedgerEntry]:
        """Fully evaluate one Collatz candidate and return a LedgerEntry."""
        try:
            cs = CollatzSequence(starting_value=candidate)
        except (OverflowError, Exception) as exc:
            logger.debug("CollatzSequence(%d) failed: %s", candidate, exc)
            return None

        features = self._extractor.extract(cs.sequence)
        stopping_time = cs.stopping_time or 0
        max_value = cs.max_value or candidate
        nm_score = self._near_miss_score(candidate, features, stopping_time, max_value)

        # Convergence verdict: 1 = converged to 1, 0 = non-convergent, 0.5 = hit limit
        converged = int(cs.metadata.get("converged", True))
        cycle_detected = int(cs.metadata.get("cycle_detected", False))

        return LedgerEntry(
            candidate=candidate,
            conjecture="collatz",
            strategy="inverse_tree_beam_search",
            features=features,
            near_miss_score=nm_score,
            details={
                "stopping_time": stopping_time,
                "max_value": max_value,
                "sequence_length": len(cs.sequence),
                "converged": converged,
                "cycle_detected": cycle_detected,
                "computation_time_s": cs.computation_time,
                # Expected stopping time for reference
                "expected_stopping_time": _EXPECTED_ST_SCALE * math.log2(max(candidate, 2)),
            },
            timestamp=time.time(),
            rng_seed=base_seed,
        )


# ── Goldbach Falsifier ────────────────────────────────────────────────────────


class GoldbachFalsifier:
    """Directed search for Goldbach counterexample candidates.

    Algorithm
    ─────────
    1. Precompute primes up to _SIEVE_LIMIT once.
    2. Generate candidates from "structurally sparse" families (see below).
    3. For each candidate, compute actual G(n) and Hardy-Littlewood G̃(n).
    4. Score by deficit: near_miss = 1 - G(n)/G̃(n).
    5. Apply algebraic filters from AlgebraicExtensions.py to compute a
       "structural hardness" bonus that boosts candidates with few allowed
       residue classes.
    6. Record to ledger.

    Sparse candidate families (decreasing expected partition count):
      A. Powers of 2: n = 2^k — no odd prime factors ⟹ empty Euler product,
         minimal singular-series correction.
      B. n = 2·p for large prime p — the single factor (p-1)/(p-2) → 1 as p → ∞.
      C. n ≡ 2 (mod 6): not divisible by 3, missing the (3-1)/(3-2) = 2× boost.
      D. n ≡ 2 (mod 30): not divisible by 3 or 5, missing both boosts.

    Why deficit, not absolute partition count?
    G(n) grows roughly as n/(log n)², so comparing raw counts across scales is
    misleading.  The deficit measures how anomalous n is RELATIVE TO ITS SCALE.
    """

    def __init__(self, sieve_limit: int = _SIEVE_LIMIT) -> None:
        self._primes: List[int] = eratosthenes(sieve_limit)
        self._prime_set: Set[int] = set(self._primes)
        # Small primes used in the H-L Euler product correction (up to sqrt of max n)
        self._small_primes: List[int] = [p for p in self._primes if p >= 3 and p <= 1000]

    # ── Hardy-Littlewood prediction ───────────────────────────────────────────

    def _hardy_littlewood_expected(self, n: int) -> float:
        """Predict G(n) via Hardy-Littlewood Conjecture B.

        G(n) ≈ 2·C₂ · ∏_{p|n, p≥3 prime} (p-1)/(p-2) · n / (log n)²

        The Euler product factor ∏(p-1)/(p-2) is > 1 for every odd prime divisor,
        meaning that numbers with small odd prime factors are predicted to have
        MORE partitions than those without.  Numbers avoiding all small odd primes
        have the minimum prediction, making them the hardest candidates.

        Returns 0.0 for n < 4 or n odd (formula inapplicable).
        """
        if n < 4 or n % 2 != 0:
            return 0.0
        ln_n = math.log(n)
        if ln_n <= 0:
            return 0.0

        # Compute Euler product correction over odd prime factors of n.
        correction = 1.0
        temp = n
        for p in self._small_primes:
            if p * p > temp and temp > 1:
                # temp itself is a prime factor > sqrt(n); add its correction.
                correction *= (temp - 1) / max(1, temp - 2)
                break
            if temp % p == 0:
                correction *= (p - 1) / (p - 2)
                while temp % p == 0:
                    temp //= p
            if temp == 1:
                break

        return 2.0 * _C2 * correction * n / (ln_n ** 2)

    def _actual_partition_count(self, n: int) -> int:
        """Count Goldbach pairs (p, q) with p + q = n, p ≤ q, both prime.

        Uses the precomputed prime set for O(π(n/2)) time per query.
        """
        if n < 4 or n % 2 != 0:
            return 0
        count = 0
        for p in self._primes:
            if p > n // 2:
                break
            if (n - p) in self._prime_set:
                count += 1
        return count

    # ── Near-miss and structural hardness ─────────────────────────────────────

    def _near_miss_score(self, actual: int, expected: float) -> float:
        """Near-miss score = 1 - actual/expected, bounded to [0, 1].

        Interpretation:
          0.0 — actual matches prediction exactly (fully explained)
          0.9 — actual is only 10% of prediction (highly anomalous)
          1.0 — actual = 0, which is a confirmed counterexample

        We use a log-ratio to avoid extreme sensitivity when expected is small:
          deficit = 1 - actual / max(1, expected)
        Floored at 0 to keep scores non-negative.
        """
        if expected <= 0:
            # No prediction available — assign 0 rather than fabricating evidence
            return 0.0
        deficit = 1.0 - actual / expected
        return max(0.0, min(1.0, deficit))

    def _structural_hardness(self, n: int) -> float:
        """Algebraic hardness bonus from AlgebraicExtensions filters.

        Two signals:
          allowed_classes : from mod_class_prune(n, mod=6).
            Fewer allowed residue classes ⟹ fewer candidate primes ⟹ harder.
            Score = 1 - len(allowed) / (mod - 1).
          warnings        : from composite_precheck(n).
            Each warning increases the hardness score.

        Combined: hardness = 0.6 * residue_score + 0.4 * warning_score
        Capped at 1.0.

        We suppress the JSON telemetry these functions emit to stdout so the
        engine log stays clean.
        """
        with contextlib.redirect_stdout(io.StringIO()):
            prune = mod_class_prune(n, mod=6)
            precheck = composite_precheck(n)

        mod = prune["modulus"]
        n_allowed = len(prune["allowed_classes"])
        # Maximum possible allowed classes for this mod is mod - 1 (excluding 0)
        residue_score = 1.0 - n_allowed / max(1, mod - 1)

        n_warnings = len(precheck.get("warnings", []))
        # Cap warning contribution at 1 warning (it's binary in practice)
        warning_score = min(1.0, n_warnings / 1.0)

        return min(1.0, 0.6 * residue_score + 0.4 * warning_score)

    # ── Candidate generation ──────────────────────────────────────────────────

    def _generate_sparse_candidates(
        self, budget: int, rng: np.random.Generator, max_n: int = 100_000
    ) -> Iterator[int]:
        """Generate even candidates from the sparsest structural families.

        Yield order (from most to least structurally sparse):
          1. Powers of 2 up to max_n — no odd prime factors at all
          2. 2·p for primes p in the upper quartile of our sieve
          3. Even n ≡ 2 (mod 30) in [1000, max_n] — avoids 3 and 5
          4. Even n ≡ 2 (mod 6) in [1000, max_n] — avoids 3

        Total distinct candidates is bounded by budget; we cycle through the
        families in priority order and stop when budget is exhausted.
        """
        seen: Set[int] = set()
        yielded = 0

        # Family 1: powers of 2
        k = 2
        while 2**k <= max_n and yielded < budget:
            n = 2**k
            if n >= 4 and n not in seen:
                seen.add(n)
                yield n
                yielded += 1
            k += 1

        # Family 2: 2·p for large primes p (upper quartile of sieve)
        upper_quarter = self._primes[3 * len(self._primes) // 4:]
        rng.shuffle(upper_quarter := list(upper_quarter))
        for p in upper_quarter:
            if yielded >= budget:
                break
            n = 2 * p
            if n <= max_n and n not in seen:
                seen.add(n)
                yield n
                yielded += 1

        # Family 3: n ≡ 2 (mod 30) — avoids multiples of 3 and 5
        candidates_30 = list(range(32, max_n + 1, 30))  # 2 mod 30 means start at 32
        rng.shuffle(candidates_30)
        for n in candidates_30:
            if yielded >= budget:
                break
            if n % 2 == 0 and n not in seen:
                seen.add(n)
                yield n
                yielded += 1

        # Family 4: n ≡ 2 (mod 6) fill remaining budget
        candidates_6 = list(range(8, max_n + 1, 6))  # 2 mod 6 means 8, 14, 20...
        rng.shuffle(candidates_6)
        for n in candidates_6:
            if yielded >= budget:
                break
            if n % 2 == 0 and n not in seen:
                seen.add(n)
                yield n
                yielded += 1

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, budget: int, seed: int) -> FalsificationLedger:
        """Run the Hardy-Littlewood deficit search.

        Parameters
        ──────────
        budget : number of candidates to evaluate
        seed   : RNG seed for reproducibility

        Returns
        ───────
        FalsificationLedger, with near-miss scores measuring structural anomaly.
        If any candidate with score 1.0 is found, a CRITICAL log is emitted
        — this would be an actual counterexample to Goldbach's conjecture.
        """
        rng = np.random.default_rng(seed)
        ledger = FalsificationLedger()

        gen = self._generate_sparse_candidates(budget, rng)
        evaluated = 0

        for candidate in gen:
            entry = self._evaluate(candidate, seed)
            ledger.append(entry)
            evaluated += 1

            if entry.near_miss_score >= 1.0:
                logger.critical(
                    "POTENTIAL GOLDBACH COUNTEREXAMPLE: n=%d, G(n)=%d, G̃(n)=%.2f",
                    candidate,
                    entry.details["actual_partitions"],
                    entry.details["expected_partitions"],
                )

            if evaluated % 100 == 0:
                logger.info(
                    "Goldbach search: %d/%d | top near-miss: %.4f",
                    evaluated,
                    budget,
                    ledger.top_k(1)[0].near_miss_score if ledger else 0.0,
                )

        logger.info("Goldbach search complete: %d candidates evaluated", evaluated)
        return ledger

    def _evaluate(self, candidate: int, base_seed: int) -> LedgerEntry:
        """Fully evaluate one Goldbach candidate."""
        actual = self._actual_partition_count(candidate)
        expected = self._hardy_littlewood_expected(candidate)
        nm_score = self._near_miss_score(actual, expected)

        # Structural hardness is an additive bonus that sharpens the ranking
        # among candidates with the same deficit score.
        # We blend: final_score = 0.85 * deficit + 0.15 * hardness
        # The 15% structural contribution is secondary — it can distinguish two
        # candidates with identical deficit but different algebraic properties.
        hardness = 0.0
        if candidate <= 100_000:
            # Algebraic filter is expensive; only apply within sieve range
            hardness = self._structural_hardness(candidate)

        blended_score = min(1.0, 0.85 * nm_score + 0.15 * hardness)

        return LedgerEntry(
            candidate=candidate,
            conjecture="goldbach",
            strategy="hardy_littlewood_deficit_search",
            features={
                "actual_partitions": float(actual),
                "expected_partitions": expected,
                "deficit_ratio": nm_score,
                "structural_hardness": hardness,
            },
            near_miss_score=blended_score,
            details={
                "actual_partitions": actual,
                "expected_partitions": round(expected, 4),
                "deficit_ratio": round(nm_score, 6),
                "structural_hardness": round(hardness, 4),
                "is_power_of_two": (candidate & (candidate - 1)) == 0,
                "mod_6_residue": candidate % 6,
                "mod_30_residue": candidate % 30,
            },
            timestamp=time.time(),
            rng_seed=base_seed,
        )


# ── FalsificationEngine ───────────────────────────────────────────────────────


class FalsificationEngine:
    """Orchestrates both falsifiers and produces a unified, ranked ledger.

    Usage
    ─────
        engine = FalsificationEngine()
        result = engine.run(budget=500, seed=42, target="both")
        result["ledger"].save(Path("falsification_ledger.jsonl"))
    """

    def __init__(self, sieve_limit: int = _SIEVE_LIMIT) -> None:
        self._collatz = CollatzFalsifier()
        self._goldbach = GoldbachFalsifier(sieve_limit=sieve_limit)
        self._riemann: Optional[Any] = None  # lazy-loaded; requires mpmath

    def _get_riemann(self) -> Any:
        if self._riemann is None:
            from codebase.FalsificationEngine.RiemannFalsifier import RiemannFalsifier
            self._riemann = RiemannFalsifier()
        return self._riemann

    def run(
        self,
        budget: int,
        seed: int,
        target: str = "both",
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Run falsification search and return a summary dict.

        Parameters
        ──────────
        budget    : total evaluation budget (split evenly between engines if
                    target == "both")
        seed      : master seed; each sub-engine receives a deterministically
                    derived child seed so results are jointly reproducible
        target    : "collatz", "goldbach", or "both"
        min_score : drop ledger entries below this near-miss score before
                    returning (reduces JSONL noise when saving large runs)

        Returns
        ───────
        {
            "ledger"         : FalsificationLedger (all entries),
            "top_collatz"    : top-5 Collatz near-misses,
            "top_goldbach"   : top-5 Goldbach near-misses,
            "stats"          : summary statistics,
            "elapsed_s"      : wall-clock seconds,
        }
        """
        _VALID_TARGETS = {"collatz", "goldbach", "riemann", "both", "all"}
        if target not in _VALID_TARGETS:
            raise ValueError(
                f"target must be one of {sorted(_VALID_TARGETS)}; got {target!r}"
            )

        run_collatz = target in {"collatz", "both", "all"}
        run_goldbach = target in {"goldbach", "both", "all"}
        run_riemann = target in {"riemann", "all"}

        t0 = time.perf_counter()
        rng_master = np.random.default_rng(seed)

        # Derive independent child seeds using the master RNG to preserve
        # reproducibility even if the user only runs one target.
        child_seeds = rng_master.integers(0, 2**31, size=3).tolist()
        collatz_seed = int(child_seeds[0])
        goldbach_seed = int(child_seeds[1])
        riemann_seed = int(child_seeds[2])

        collatz_ledger = FalsificationLedger()
        goldbach_ledger = FalsificationLedger()
        riemann_ledger = FalsificationLedger()

        # Split budget across active engines.
        n_active = sum([run_collatz, run_goldbach, run_riemann])
        per_engine = max(1, budget // n_active)
        remainder = budget - per_engine * n_active

        collatz_budget = (per_engine + remainder) if run_collatz else 0
        goldbach_budget = per_engine if run_goldbach else 0
        riemann_budget = per_engine if run_riemann else 0

        if run_collatz and run_goldbach and not run_riemann:
            # Original "both" path: run the two fast engines in parallel.
            logger.info(
                "Starting parallel falsification (collatz budget=%d seed=%d, "
                "goldbach budget=%d seed=%d)",
                collatz_budget, collatz_seed, goldbach_budget, goldbach_seed,
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                cf = pool.submit(self._collatz.search, collatz_budget, collatz_seed)
                gf = pool.submit(self._goldbach.search, goldbach_budget, goldbach_seed)
                collatz_ledger = cf.result()
                goldbach_ledger = gf.result()
        else:
            # Sequential for single-engine or all-engine runs (Riemann is slow).
            if run_collatz:
                logger.info(
                    "Starting Collatz falsification (budget=%d, seed=%d)",
                    collatz_budget, collatz_seed,
                )
                collatz_ledger = self._collatz.search(collatz_budget, collatz_seed)

            if run_goldbach:
                logger.info(
                    "Starting Goldbach falsification (budget=%d, seed=%d)",
                    goldbach_budget, goldbach_seed,
                )
                goldbach_ledger = self._goldbach.search(goldbach_budget, goldbach_seed)

            if run_riemann:
                logger.info(
                    "Starting Riemann falsification (budget=%d, seed=%d)",
                    riemann_budget, riemann_seed,
                )
                riemann_ledger = self._get_riemann().search(riemann_budget, riemann_seed)

        all_ledgers = [collatz_ledger, goldbach_ledger, riemann_ledger]
        merged = self._merge_ledgers(all_ledgers, min_score=min_score)

        elapsed = time.perf_counter() - t0
        logger.info(
            "FalsificationEngine complete: %d total entries (min_score=%.2f) in %.2fs",
            len(merged), min_score, elapsed,
        )

        return {
            "ledger": merged,
            "top_collatz": collatz_ledger.top_k(5),
            "top_goldbach": goldbach_ledger.top_k(5),
            "top_riemann": riemann_ledger.top_k(5),
            "stats": {
                "collatz_evaluated": len(collatz_ledger),
                "goldbach_evaluated": len(goldbach_ledger),
                "riemann_evaluated": len(riemann_ledger),
                "total_evaluated": len(merged),
                "collatz_max_near_miss": (
                    collatz_ledger.top_k(1)[0].near_miss_score if collatz_ledger else 0.0
                ),
                "goldbach_max_near_miss": (
                    goldbach_ledger.top_k(1)[0].near_miss_score if goldbach_ledger else 0.0
                ),
                "riemann_max_near_miss": (
                    riemann_ledger.top_k(1)[0].near_miss_score if riemann_ledger else 0.0
                ),
                "seed": seed,
                "elapsed_s": round(elapsed, 3),
            },
            "elapsed_s": elapsed,
        }

    @staticmethod
    def _merge_ledgers(
        ledgers: List[FalsificationLedger], min_score: float = 0.0
    ) -> FalsificationLedger:
        """Merge multiple ledgers, dropping entries below min_score."""
        merged = FalsificationLedger()
        for ledger in ledgers:
            for entry in ledger._entries:
                if entry.near_miss_score >= min_score:
                    merged.append(entry)
        return merged


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="ProofX FalsificationEngine — directed counterexample search"
    )
    parser.add_argument("--budget", type=int, default=200,
                        help="Total evaluation budget (default 200)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for reproducible search (default 42)")
    parser.add_argument("--target",
                        choices=["collatz", "goldbach", "riemann", "both", "all"],
                        default="both",
                        help="Which conjecture to search (default both)")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of top near-misses to print per conjecture")
    parser.add_argument("--save-ledger", type=str, default=None,
                        help="Path to save the full ledger as JSONL (optional)")
    parser.add_argument("--output-json", type=str, default=None,
                        help="Path to save a JSON summary report (optional)")
    parser.add_argument("--sieve-limit", type=int, default=_SIEVE_LIMIT,
                        help=f"Upper bound for the Goldbach prime sieve (default {_SIEVE_LIMIT})")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Drop ledger entries with near-miss score below this value (default 0)")
    args = parser.parse_args()

    engine = FalsificationEngine(sieve_limit=args.sieve_limit)
    result = engine.run(budget=args.budget, seed=args.seed, target=args.target,
                        min_score=args.min_score)

    stats = result["stats"]
    print(f"\n{'═'*60}")
    print(f"  FalsificationEngine Results  (seed={args.seed})")
    print(f"{'═'*60}")
    print(f"  Collatz evaluated   : {stats['collatz_evaluated']}")
    print(f"  Goldbach evaluated  : {stats['goldbach_evaluated']}")
    print(f"  Elapsed             : {stats['elapsed_s']:.2f}s")

    for label, key in [
        ("Collatz top near-misses", "top_collatz"),
        ("Goldbach top near-misses", "top_goldbach"),
        ("Riemann top near-misses", "top_riemann"),
    ]:
        entries = result.get(key, [])
        if not entries:
            continue
        print(f"\n  {label}:")
        for i, e in enumerate(entries[:args.top_k], 1):
            print(f"    #{i}  n={e.candidate:>12,}  near_miss={e.near_miss_score:.4f}"
                  f"  strategy={e.strategy}")

    if args.save_ledger:
        result["ledger"].save(Path(args.save_ledger))
        print(f"\n  Ledger saved: {args.save_ledger}")

    if args.output_json:
        summary = {
            "seed": args.seed,
            "budget": args.budget,
            "target": args.target,
            "elapsed_s": stats["elapsed_s"],
            "stats": stats,
            "top_collatz": [
                {
                    "candidate": e.candidate,
                    "near_miss_score": e.near_miss_score,
                    "strategy": e.strategy,
                    "features": e.features,
                }
                for e in result["top_collatz"][: args.top_k]
            ],
            "top_goldbach": [
                {
                    "candidate": e.candidate,
                    "near_miss_score": e.near_miss_score,
                    "strategy": e.strategy,
                    "features": e.features,
                }
                for e in result["top_goldbach"][: args.top_k]
            ],
        }
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\n  JSON summary saved: {args.output_json}")


if __name__ == "__main__":
    main()
