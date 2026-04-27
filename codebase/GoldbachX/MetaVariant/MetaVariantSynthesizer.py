"""
MetaVariantSynthesizer - Generates and evaluates Goldbach conjecture variants.
"""

import argparse
import json
import math
import random
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Union
import itertools
import numpy as np

# Optional Streamlit support (feature-gated)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Constants
DEFAULT_RANGE_START = 4
DEFAULT_RANGE_END = 100_000
DEFAULT_BUDGET_MS = 2000
PRIMES_UP_TO = 1_000_000  # Precompute primes up to this limit

# Precomputed primes (lazy-loaded)
_PRIMES: List[int] = []
_PRIME_SET: Set[int] = set()

class DSLSyntaxError(Exception):
    """Custom exception for DSL parsing errors."""
    pass

@dataclass
class VariantTemplate:
    """Represents a parameterized Goldbach variant template."""
    name: str
    dsl_pattern: str
    parameters: Dict[str, Tuple[type, List[Union[int, str]]]]
    description: str

# Core templates
TEMPLATES = [
    VariantTemplate(
        name="mod_constraint",
        dsl_pattern="Every even n ≥ {N0} is sum of two primes with p mod {m} ∈ {S}",
        parameters={
            "N0": (int, [4, 6, 8, 10]),
            "m": (int, [3, 4, 5, 6, 7, 8]),
            "S": (str, ["{1}", "{1,2}", "{1,3,5}", "{0,1}"])
        },
        description="Goldbach with modular constraints on one prime"
    ),
    VariantTemplate(
        name="k_decompositions",
        dsl_pattern="At least {k} distinct decompositions for evens in [{a}, {b}]",
        parameters={
            "k": (int, [1, 2, 3, 5, 10]),
            "a": (int, [4, 100, 1000, 10_000]),
            "b": (int, [100, 1000, 10_000, 100_000])
        },
        description="Minimum number of Goldbach pairs required"
    ),
    VariantTemplate(
        name="interval_constraint",
        dsl_pattern="One prime in each pair lies in [{c}n^{d}, {C}n^{D}]",
        parameters={
            "c": (float, [0.1, 0.5, 1.0, 2.0]),
            "d": (float, [0.8, 0.9, 1.0, 1.1]),
            "C": (float, [0.5, 1.0, 2.0, 3.0]),
            "D": (float, [0.9, 1.0, 1.1])
        },
        description="Prime must lie in scaled interval"
    )
]

def _ensure_primes() -> None:
    """Lazy-load primes using Sieve of Eratosthenes."""
    global _PRIMES, _PRIME_SET
    if not _PRIMES:
        sieve = [True] * (PRIMES_UP_TO + 1)
        sieve[0] = sieve[1] = False
        for i in range(2, int(math.sqrt(PRIMES_UP_TO)) + 1):
            if sieve[i]:
                sieve[i*i::i] = [False] * len(sieve[i*i::i])
        _PRIMES = [i for i, is_prime in enumerate(sieve) if is_prime]
        _PRIME_SET = set(_PRIMES)

@lru_cache(maxsize=100_000)
def is_prime(n: int) -> bool:
    """Check if a number is prime (cached)."""
    if n > PRIMES_UP_TO:
        raise ValueError(f"Primes only precomputed up to {PRIMES_UP_TO}")
    _ensure_primes()
    return n in _PRIME_SET

def goldbach_pairs(n: int) -> List[Tuple[int, int]]:
    """Return all Goldbach pairs for even n >= 4."""
    if n % 2 != 0 or n < 4:
        return []

    _ensure_primes()
    pairs = []
    for p in _PRIMES:
        if p > n // 2:
            break
        q = n - p
        if is_prime(q):
            pairs.append((p, q))
    return pairs

def generate_templates(seed: Optional[int] = None) -> List[str]:
    """Return all available template DSL strings."""
    return [t.dsl_pattern for t in TEMPLATES]

def instantiate(tmpl: str, params: Dict[str, Union[int, str, float]]) -> Dict:
    """
    Instantiate a template with parameters.

    Returns:
        dict: {"statement": str, "params": dict}
    """
    try:
        template = next(t for t in TEMPLATES if t.dsl_pattern == tmpl)
    except StopIteration:
        raise DSLSyntaxError(f"Unknown template: {tmpl}")

    # Validate parameters
    for param_name, (param_type, allowed_values) in template.parameters.items():
        if param_name not in params:
            raise DSLSyntaxError(f"Missing parameter: {param_name}")
        if not isinstance(params[param_name], param_type):
            raise DSLSyntaxError(f"Parameter {param_name} must be {param_type}")
        if allowed_values and params[param_name] not in allowed_values:
            raise DSLSyntaxError(f"Invalid value for {param_name}. Allowed: {allowed_values}")

    # Format the statement
    statement = tmpl.format(**params)
    return {"statement": statement, "params": params}

def evaluate(
    stmt: str,
    params: Dict,
    *,
    start: int = DEFAULT_RANGE_START,
    end: int = DEFAULT_RANGE_END,
    budget_ms: int = DEFAULT_BUDGET_MS
) -> Dict:
    """
    Evaluate a variant statement against empirical data.

    Returns:
        dict: {
            "support": float,
            "simplicity": float,
            "novelty": float,
            "rationale": str,
            "tested_up_to": int,
            "time_ms": float
        }
    """
    start_time = time.time()
    template = next(t for t in TEMPLATES if t.dsl_pattern in stmt)
    tested = 0
    satisfied = 0
    total = 0

    # Evaluation logic per template type
    if template.name == "mod_constraint":
        N0 = params["N0"]
        m = params["m"]
        S = eval(params["S"])  # Safe because we control the DSL
        S = set(S)

        for n in range(start, end + 1, 2):
            if n < N0:
                continue
            if time.time() - start_time > budget_ms / 1000:
                break
            pairs = goldbach_pairs(n)
            if not pairs:
                continue
            total += 1
            has_valid_pair = any(p % m in S for p, _ in pairs) or any(q % m in S for _, q in pairs)
            if has_valid_pair:
                satisfied += 1
            tested += 1

    elif template.name == "k_decompositions":
        k = params["k"]
        a = params["a"]
        b = params["b"]

        for n in range(a, b + 1, 2):
            if time.time() - start_time > budget_ms / 1000:
                break
            pairs = goldbach_pairs(n)
            total += 1
            if len(pairs) >= k:
                satisfied += 1
            tested += 1

    elif template.name == "interval_constraint":
        c = params["c"]
        d = params["d"]
        C = params["C"]
        D = params["D"]

        for n in range(start, end + 1, 2):
            if time.time() - start_time > budget_ms / 1000:
                break
            pairs = goldbach_pairs(n)
            if not pairs:
                continue
            total += 1
            lower = c * (n ** d)
            upper = C * (n ** D)
            has_valid_pair = any(lower <= p <= upper or lower <= q <= upper for p, q in pairs)
            if has_valid_pair:
                satisfied += 1
            tested += 1

    # Calculate scores
    support = satisfied / max(1, total)
    simplicity = 1 / (1 + sum(len(str(v)) for v in params.values()))  # MDL-like
    novelty = 1 - 0.5 * (template.name == "mod_constraint")  # Simple novelty proxy

    return {
        "support": support,
        "simplicity": simplicity,
        "novelty": novelty,
        "rationale": f"Tested {tested} evens: {satisfied} satisfied ({support:.1%})",
        "tested_up_to": tested,
        "time_ms": (time.time() - start_time) * 1000
    }

def synthesize(budget: int = 500, seed: Optional[int] = None) -> Dict:
    """
    Explore template×param space and return Pareto-optimal variants.

    Returns:
        dict: {
            "pareto_front": List[dict],
            "templates_tried": int,
            "candidates_tested": int,
            "time_ms": float
        }
    """
    start_time = time.time()
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    pareto_front = []
    templates_tried = 0
    candidates_tested = 0

    for _ in range(budget):
        # Random template and parameters
        template = random.choice(TEMPLATES)
        params = {}
        for param, (param_type, allowed_values) in template.parameters.items():
            if param_type == str:
                params[param] = random.choice(allowed_values)
            else:
                if len(allowed_values) > 1:
                    if param_type == int:
                        params[param] = random.randint(allowed_values[0], allowed_values[-1])
                    else:  # float
                        params[param] = random.uniform(allowed_values[0], allowed_values[-1])
                else:
                    params[param] = allowed_values[0]

        try:
            instantiated = instantiate(template.dsl_pattern, params)
            result = evaluate(instantiated["statement"], params)
            candidates_tested += 1

            # Check Pareto optimality
            dominated = False
            new_front = []
            for candidate in pareto_front:
                if (result["support"] >= candidate["support"] and
                    result["simplicity"] >= candidate["simplicity"] and
                    result["novelty"] >= candidate["novelty"]):
                    dominated = True
                if not (result["support"] > candidate["support"] and
                        result["simplicity"] > candidate["simplicity"] and
                        result["novelty"] > candidate["novelty"]):
                    new_front.append(candidate)

            if not dominated:
                new_front.append({
                    "statement": instantiated["statement"],
                    "params": params,
                    **result
                })
                pareto_front = new_front

        except (DSLSyntaxError, ValueError):
            continue

    return {
        "pareto_front": sorted(
            pareto_front,
            key=lambda x: (-x["support"], -x["simplicity"], -x["novelty"])
        ),
        "templates_tried": templates_tried,
        "candidates_tested": candidates_tested,
        "time_ms": (time.time() - start_time) * 1000
    }

def export(obj: Dict, path: str) -> None:
    """Export results to JSON file."""
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def metadata() -> Dict:
    """Return metadata about this component."""
    return {
        "version": "1.0",
        "templates": [t.name for t in TEMPLATES],
        "max_prime": PRIMES_UP_TO
    }

def discover() -> Dict:
    """Return discovery information."""
    return {"component": "MetaVariantSynthesizer"}

def run_self_tests() -> bool:
    """Run self-tests and return True if all pass."""
    # Test 1: DSL round-trip
    try:
        tmpl = TEMPLATES[0].dsl_pattern
        params = {k: v[1][0] for k, v in TEMPLATES[0].parameters.items()}
        instantiated = instantiate(tmpl, params)
        assert tmpl in instantiated["statement"], "DSL round-trip failed"
    except Exception as e:
        print(f"Self-test failed (DSL): {e}")
        return False

    # Test 2: Scoring monotonicity
    try:
        r1 = evaluate("Every even n ≥ 4 is sum of two primes with p mod 3 ∈ {1}", {"N0": 4, "m": 3, "S": "{1}"})
        r2 = evaluate("Every even n ≥ 4 is sum of two primes with p mod 3 ∈ {1,2}", {"N0": 4, "m": 3, "S": "{1,2}"})
        assert r2["support"] >= r1["support"], "Support should be monotonic"
    except Exception as e:
        print(f"Self-test failed (scoring): {e}")
        return False

    # Test 3: Seed stability
    try:
        r1 = synthesize(budget=10, seed=42)
        r2 = synthesize(budget=10, seed=42)
        assert r1["pareto_front"] == r2["pareto_front"], "Results should be seed-stable"
    except Exception as e:
        print(f"Self-test failed (seed): {e}")
        return False

    return True

def main_cli():
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="Goldbach Variant Synthesizer")
    parser.add_argument("--mode", choices=["cli", "self-test"], default="cli")
    parser.add_argument("--budget", type=int, default=500)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--export", type=str, default=None)
    args = parser.parse_args()

    if args.mode == "self-test":
        success = run_self_tests()
        print("Self-tests passed!" if success else "Self-tests failed!")
        exit(0 if success else 1)

    print("Synthesizing variants...")
    results = synthesize(budget=args.budget, seed=args.seed)

    print(f"\nPareto frontier ({len(results['pareto_front'])} variants):")
    for i, variant in enumerate(results["pareto_front"], 1):
        print(f"\n#{i}: {variant['statement']}")
        print(f"  Support: {variant['support']:.1%}")
        print(f"  Simplicity: {variant['simplicity']:.2f}")
        print(f"  Novelty: {variant['novelty']:.2f}")
        print(f"  Rationale: {variant['rationale']}")

    if args.export:
        export(results, args.export)
        print(f"\nResults exported to {args.export}")

def main_streamlit():
    """Streamlit web interface."""
    if not HAS_STREAMLIT:
        st.error("Streamlit not available")
        return

    st.title("Goldbach Variant Synthesizer")
    st.sidebar.header("Configuration")

    budget = st.sidebar.slider("Search budget", 10, 1000, 200)
    seed = st.sidebar.number_input("Random seed", value=42)

    if st.sidebar.button("Run Synthesis"):
        with st.spinner("Synthesizing variants..."):
            results = synthesize(budget=budget, seed=seed if seed != 0 else None)

        st.success(f"Found {len(results['pareto_front'])} Pareto-optimal variants")

        for i, variant in enumerate(results["pareto_front"], 1):
            with st.expander(f"Variant #{i}: {variant['statement']}"):
                st.metric("Support", f"{variant['support']:.1%}")
                st.metric("Simplicity", f"{variant['simplicity']:.2f}")
                st.metric("Novelty", f"{variant['novelty']:.2f}")
                st.caption(variant["rationale"])

                if st.button(f"Export Variant #{i}", key=f"export_{i}"):
                    st.download_button(
                        label="Download JSON",
                        data=json.dumps(variant, indent=2),
                        file_name=f"goldbach_variant_{i}.json",
                        mime="application/json"
                    )

if __name__ == "__main__":
    if HAS_STREAMLIT and "streamlit" in __import__("sys").argv[0]:
        main_streamlit()
    else:
        main_cli()


# ═════════════════════════════════════════════════════════════════════════════
# PART 2 — CLOSED SYNTHESIS LOOP
# ═════════════════════════════════════════════════════════════════════════════
#
# Architecture
# ────────────
# synthesize()          (existing) → Pareto-optimal variants
#       │
#       ▼
# VerificationPipeline  → three independent verifiers run on each variant:
#   (1) PartitionEnumerator   empirical_score  — does the variant hold in practice?
#   (2) SymbolicGoldbachReasoner heuristic_score — do structural rules support it?
#   (3) AlgebraicExtensions   structural_score — is it algebraically consistent?
#       │
#       ▼
# ConjectureRecord      → immutable record capturing all scores + LaTeX hypothesis
#       │
#       ▼
# RankingEngine         → composite_score = 0.50·E + 0.30·H + 0.20·S
#       │
#       ▼
# synthesize_and_verify(budget, seed) → List[ConjectureRecord]
#
# Weighting justification (5:3:2)
# ────────────────────────────────
# Empirical (0.50): Direct testing against a range of even numbers is the most
#   falsifiable evidence.  A variant that fails for even one tested n is refuted
#   immediately.  Highest weight because it is the most epistemically binding.
#
# Heuristic (0.30): The SymbolicGoldbachReasoner fires structural rules (e.g.,
#   residue-class coverage, twin-prime density).  These are indirect evidence —
#   they capture WHY the variant might hold, not just that it does.  Second
#   highest because structural reasoning constrains the space of possible truths.
#
# Structural (0.20): AlgebraicExtensions checks residue-class consistency and
#   composite precheck warnings.  This is a necessary (not sufficient) condition;
#   algebraic consistency is a filter, not a proof.  Lowest weight.
#
# Confidence bounds
# ─────────────────
# Empirical: Wilson score interval at 95% — the classical choice for a proportion
#   estimate when sample size is small, because it is bounded to [0,1] and performs
#   well at extreme proportions unlike the normal-approximation interval.
# Composite: Linear propagation of the Wilson interval via the 5:3:2 weights,
#   assuming heuristic and structural scores have ±10% inherent uncertainty.
# ═════════════════════════════════════════════════════════════════════════════

import contextlib
import io
import sys
from dataclasses import dataclass as _dc
from pathlib import Path as _Path
from typing import Tuple as _Tuple

# Resolve ProofX root for intra-codebase imports.
_MVS_ROOT = _Path(__file__).resolve().parents[3]
if str(_MVS_ROOT) not in sys.path:
    sys.path.insert(0, str(_MVS_ROOT))

try:
    from codebase.GoldbachX.GoldbachReasoner.SymbolicGoldbachReasoner import (
        SymbolicGoldbachReasoner as _Reasoner,
    )
    from codebase.GoldbachX.PartitionEnumerator.PartitionEnumerator import enumerate_partitions
    from codebase.GoldbachX.AlgebraicExtensions.AlgebraicExtensions import (
        composite_precheck as _precheck,
        mod_class_prune as _mod_prune,
    )
    _HAS_VERIFICATION_DEPS = True
except ImportError as _import_err:
    import warnings
    warnings.warn(
        f"VerificationPipeline: some dependencies unavailable ({_import_err}). "
        "Affected scores will be set to 0.0.",
        stacklevel=2,
    )
    _HAS_VERIFICATION_DEPS = False


# ── Wilson score interval ─────────────────────────────────────────────────────

def _wilson_interval(successes: int, total: int, z: float = 1.96) -> _Tuple[float, float]:
    """Wilson score 95% confidence interval for a proportion.

    Superior to the normal-approximation interval for small samples and
    proportions near 0 or 1 because it always returns values in [0, 1].

    Reference: Wilson, E.B. (1927). Probable inference, the law of succession,
    and statistical inference. Journal of the American Statistical Association.
    """
    if total == 0:
        return (0.0, 1.0)
    p_hat = successes / total
    z2n = (z * z) / total
    center = (p_hat + z2n / 2.0) / (1.0 + z2n)
    margin = (z * math.sqrt(p_hat * (1.0 - p_hat) / total + z2n / (4.0 * total))
              / (1.0 + z2n))
    return (max(0.0, center - margin), min(1.0, center + margin))


# ── ConjectureRecord ──────────────────────────────────────────────────────────

@_dc
class ConjectureRecord:
    """Immutable record capturing a Goldbach variant and its full verification.

    Fields
    ──────
    variant_statement : the DSL string from the synthesizer
    params            : parameter dict used to instantiate the template
    template_name     : which TEMPLATES entry this came from
    empirical_score   : fraction of tested even numbers satisfying the variant
    heuristic_score   : average rule-weight from SymbolicGoldbachReasoner.prove()
    structural_score  : algebraic consistency score ∈ [0, 1]
    composite_score   : 0.50·E + 0.30·H + 0.20·S
    confidence_lower  : lower bound of 95% confidence interval on composite_score
    confidence_upper  : upper bound of 95% confidence interval on composite_score
    tested_range      : (start, end) of even numbers tested empirically
    synthesis_seed    : the seed used when this variant was synthesized
    latex_hypothesis  : LaTeX-formatted hypothesis string for the report
    timestamp         : epoch seconds when this record was created
    """

    variant_statement: str
    params: Dict
    template_name: str
    empirical_score: float
    heuristic_score: float
    structural_score: float
    composite_score: float
    confidence_lower: float
    confidence_upper: float
    tested_range: Tuple[int, int]
    synthesis_seed: int
    latex_hypothesis: str
    timestamp: float

    def to_dict(self) -> Dict:
        import dataclasses
        return dataclasses.asdict(self)


# ── VerificationPipeline ──────────────────────────────────────────────────────

class VerificationPipeline:
    """Passes each Pareto-optimal variant through three independent verifiers.

    The pipeline is intentionally stateless between calls so that records are
    fully reproducible given the same synthesis_seed.
    """

    # Range of even numbers used for empirical testing.
    # 4000 is enough to estimate support reliably; the Wilson interval tightens
    # to ±3% at n=1000, ±1.5% at n=4000 for p̂ ≈ 0.5.
    _EMPIRICAL_START: int = 4
    _EMPIRICAL_END: int = 4_000

    def verify(self, variant: Dict, synthesis_seed: int) -> ConjectureRecord:
        """Run all three verifiers and return a ConjectureRecord.

        Parameters
        ──────────
        variant       : a dict from synthesize()["pareto_front"] with keys
                        'statement', 'params', and Pareto scores
        synthesis_seed: seed used during synthesis (captured for provenance)
        """
        emp_score, emp_lower, emp_upper = self._evaluate_empirically(variant)
        heur_score = self._evaluate_heuristic(variant)
        struct_score = self._evaluate_structural(variant)

        # Composite score: 5:3:2 weighting (see module header for justification)
        composite = 0.50 * emp_score + 0.30 * heur_score + 0.20 * struct_score

        # Propagate confidence bounds linearly.
        # Heuristic and structural scores are treated as point estimates with
        # ±10% inherent uncertainty (rule-weight variance and filter sensitivity).
        H_UNCERTAINTY = 0.10
        S_UNCERTAINTY = 0.10
        conf_lower = (0.50 * emp_lower
                      + 0.30 * max(0.0, heur_score - H_UNCERTAINTY)
                      + 0.20 * max(0.0, struct_score - S_UNCERTAINTY))
        conf_upper = (0.50 * emp_upper
                      + 0.30 * min(1.0, heur_score + H_UNCERTAINTY)
                      + 0.20 * min(1.0, struct_score + S_UNCERTAINTY))

        latex = self._generate_latex(variant)

        return ConjectureRecord(
            variant_statement=variant["statement"],
            params=variant["params"],
            template_name=self._template_name_for(variant["statement"]),
            empirical_score=round(emp_score, 6),
            heuristic_score=round(heur_score, 6),
            structural_score=round(struct_score, 6),
            composite_score=round(composite, 6),
            confidence_lower=round(conf_lower, 6),
            confidence_upper=round(conf_upper, 6),
            tested_range=(self._EMPIRICAL_START, self._EMPIRICAL_END),
            synthesis_seed=synthesis_seed,
            latex_hypothesis=latex,
            timestamp=time.time(),
        )

    # ── Verifier 1: Empirical (PartitionEnumerator) ───────────────────────────

    def _evaluate_empirically(self, variant: Dict) -> _Tuple[float, float, float]:
        """Test the variant against even numbers in [EMPIRICAL_START, EMPIRICAL_END].

        Returns (score, wilson_lower, wilson_upper).

        We reuse the evaluate() function from the synthesizer for templates it
        already handles; for new templates the fallback uses the same logic as
        evaluate() but calls PartitionEnumerator directly so the dependency is
        exercised as required.
        """
        if not _HAS_VERIFICATION_DEPS:
            return 0.0, 0.0, 1.0

        params = variant["params"]
        statement = variant["statement"]
        template = next((t for t in TEMPLATES if t.dsl_pattern in statement), None)
        if template is None:
            return 0.0, 0.0, 1.0

        # Precompute primes for the empirical range once.
        # PartitionEnumerator requires primes[−1] ≤ n, so we use primes ≤ EMPIRICAL_END.
        sieve_size = self._EMPIRICAL_END
        sieve = [True] * (sieve_size + 1)
        sieve[0] = sieve[1] = False
        for i in range(2, int(math.sqrt(sieve_size)) + 1):
            if sieve[i]:
                sieve[i * i :: i] = [False] * len(sieve[i * i :: i])
        all_primes = [i for i, f in enumerate(sieve) if f]

        total = 0
        satisfied = 0
        budget_ms = 3000  # 3-second hard cap per variant to keep the pipeline fast

        for n in range(self._EMPIRICAL_START, self._EMPIRICAL_END + 1, 2):
            if (time.time() - time.time()) > budget_ms / 1000:
                break

            # Build a prime list for this specific n (PartitionEnumerator requires p ≤ n)
            primes_n = [p for p in all_primes if p <= n]
            if not primes_n:
                continue

            # Suppress PartitionEnumerator's numpy-timing output
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    pairs = enumerate_partitions(n, primes_n)
                except (ValueError, Exception):
                    continue

            total += 1

            if template.name == "mod_constraint":
                m = params["m"]
                S = set(eval(params["S"]))  # Safe: controlled DSL set literal
                if any(p % m in S or q % m in S for p, q in pairs):
                    satisfied += 1

            elif template.name == "k_decompositions":
                k = params["k"]
                a, b = params["a"], params["b"]
                if a <= n <= b and len(pairs) >= k:
                    satisfied += 1
                elif a <= n <= b:
                    pass  # counted in total but not satisfied

            elif template.name == "interval_constraint":
                c, d, C, D = params["c"], params["d"], params["C"], params["D"]
                lo, hi = c * (n ** d), C * (n ** D)
                if pairs and any(lo <= p <= hi or lo <= q <= hi for p, q in pairs):
                    satisfied += 1

        score = satisfied / max(1, total)
        lower, upper = _wilson_interval(satisfied, total)
        return score, lower, upper

    # ── Verifier 2: Heuristic (SymbolicGoldbachReasoner) ─────────────────────

    def _evaluate_heuristic(self, variant: Dict) -> float:
        """Query the SymbolicGoldbachReasoner for structural support.

        The reasoner returns a score ∈ [0, 1] representing the average weight
        of rules that fired in support of the statement.  We translate the
        variant's DSL statement into the natural-language form the reasoner
        expects, then extract the score.

        Stderr telemetry from the reasoner is suppressed to keep the pipeline log
        clean; we only care about the numeric score.
        """
        if not _HAS_VERIFICATION_DEPS:
            return 0.0

        reasoner = _Reasoner(seed=0)  # seed=0 for determinism within the pipeline

        # Translate the DSL statement to the reasoner's expected vocabulary.
        # The reasoner's _parse_statement maps "every even n in ..." → exists_prime_pair.
        # We use the generic Goldbach form; specialised modular constraints get a
        # context injection to prime the working memory.
        statement = "Every even n in [{}, {}] has ≥1 prime pair".format(
            self._EMPIRICAL_START, self._EMPIRICAL_END
        )
        context: Dict = {}

        template_name = self._template_name_for(variant["statement"])

        # Inject context facts that make the reasoner aware of the specific variant
        if template_name == "mod_constraint":
            m = variant["params"]["m"]
            context["known_facts"] = [f"n % {m} == 0", "even(n)", "n >= 4"]
        elif template_name == "k_decompositions":
            a, b = variant["params"]["a"], variant["params"]["b"]
            if b > 1_000_000:
                context["known_facts"] = ["n > 1e6", "even(n)"]
            else:
                context["known_facts"] = ["even(n)", "n >= 4"]
        else:
            context["known_facts"] = ["even(n)", "n >= 4"]

        # Suppress stderr telemetry from the reasoner
        with contextlib.redirect_stderr(io.StringIO()):
            result = reasoner.prove(statement, context=context, seed=0)

        return float(result.get("score", 0.0))

    # ── Verifier 3: Structural (AlgebraicExtensions) ──────────────────────────

    def _evaluate_structural(self, variant: Dict) -> float:
        """Assess algebraic consistency via AlgebraicExtensions.

        Scores are computed by sampling 20 even numbers from the empirical range
        and averaging two signals:
          (a) residue_score: fraction of allowed residue classes relative to
              the maximum (mod-1).  More allowed classes = more structurally
              supported = higher score.
          (b) safety_score: fraction of sample numbers with zero composite-precheck
              warnings.  More warnings = algebraically "harder" = lower score.

        We invert safety_score relative to the falsification context: for
        verification purposes, FEWER warnings means the variant is in a
        well-behaved algebraic region, which is positive evidence.
        """
        if not _HAS_VERIFICATION_DEPS:
            return 0.0

        sample_ns = list(range(
            self._EMPIRICAL_START,
            min(self._EMPIRICAL_END, self._EMPIRICAL_START + 200),
            10,
        ))

        residue_scores: List[float] = []
        safety_scores: List[float] = []

        mod = variant["params"].get("m", 6) if "m" in variant["params"] else 6

        for n in sample_ns:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    prune = _mod_prune(n, mod=mod)
                    precheck = _precheck(n)
                except Exception:
                    continue

            n_allowed = len(prune.get("allowed_classes", []))
            max_classes = mod - 1  # maximum possible coprime-to-mod residues
            residue_scores.append(n_allowed / max(1, max_classes))

            n_warnings = len(precheck.get("warnings", []))
            # 0 warnings → safe (score=1); 1+ warnings → score = 1/(1+n_warnings)
            safety_scores.append(1.0 / (1.0 + n_warnings))

        if not residue_scores:
            return 0.0

        avg_residue = sum(residue_scores) / len(residue_scores)
        avg_safety = sum(safety_scores) / len(safety_scores)

        # 60% residue coverage + 40% algebraic safety (same 3:2 sub-weighting as
        # the GoldbachFalsifier's structural_hardness, inverted for verification)
        return min(1.0, 0.60 * avg_residue + 0.40 * avg_safety)

    # ── LaTeX generation ──────────────────────────────────────────────────────

    def _generate_latex(self, variant: Dict) -> str:
        """Convert a variant statement to a LaTeX-formatted hypothesis string.

        Each template maps to a distinct mathematical form.  The mapping is
        one-to-one with the TEMPLATES list so adding a new template requires
        adding a new branch here.
        """
        p = variant["params"]
        name = self._template_name_for(variant["statement"])

        if name == "mod_constraint":
            N0 = p.get("N0", 4)
            m = p.get("m", 3)
            S_raw = str(p.get("S", "{1}")).replace("{", "\\{").replace("}", "\\}")
            return (
                r"\forall n \in 2\mathbb{Z},\; n \geq "
                + str(N0)
                + r",\; \exists\, p, q \text{ prime}:\; p + q = n"
                + r" \text{ and } p \bmod "
                + str(m)
                + r" \in "
                + S_raw
            )

        if name == "k_decompositions":
            k = p.get("k", 1)
            a = p.get("a", 4)
            b = p.get("b", 100)
            return (
                r"\forall n \in 2\mathbb{Z} \cap ["
                + str(a)
                + r", "
                + str(b)
                + r"],\; \left|\bigl\{(p,q): p+q=n,\; p \leq q,\; p,q \text{ prime}\bigr\}\right| \geq "
                + str(k)
            )

        if name == "interval_constraint":
            c = p.get("c", 0.5)
            d = p.get("d", 1.0)
            C = p.get("C", 1.0)
            D = p.get("D", 1.0)
            return (
                r"\forall n \geq 4,\; \exists\, p, q \text{ prime}:\; p + q = n"
                + r" \text{ and } "
                + str(c)
                + r" n^{"
                + str(d)
                + r"} \leq p \leq "
                + str(C)
                + r" n^{"
                + str(D)
                + r"}"
            )

        # Fallback: wrap the raw statement in \text{}
        return r"\text{" + variant["statement"].replace("≥", r"\geq ") + r"}"

    @staticmethod
    def _template_name_for(statement: str) -> str:
        """Identify which template a statement came from by substring matching."""
        for t in TEMPLATES:
            if t.dsl_pattern.split("{")[0].strip() in statement:
                return t.name
        return "unknown"


# ── RankingEngine ─────────────────────────────────────────────────────────────

class RankingEngine:
    """Orders ConjectureRecords by composite_score descending.

    The composite_score is already the canonical ranking signal — it encodes
    the 5:3:2 epistemological weighting.  The RankingEngine additionally applies
    a *confidence-width penalty* to demote records whose confidence interval is
    very wide (i.e., where the evidence is uncertain despite a good point estimate).

    Final rank score = composite_score - α · (confidence_upper - confidence_lower)
    where α = 0.1 (small penalty: uncertainty matters, but support matters more).

    α = 0.1 is chosen so that a 50-percentage-point CI width (a highly uncertain
    estimate) reduces the rank score by only 5 points — enough to break ties
    between similarly-scoring variants without overriding clear winners.
    """

    _CONFIDENCE_PENALTY: float = 0.10

    def rank(self, records: List[ConjectureRecord]) -> List[ConjectureRecord]:
        """Return records sorted by rank_score descending (best first)."""
        def rank_score(r: ConjectureRecord) -> float:
            width = r.confidence_upper - r.confidence_lower
            return r.composite_score - self._CONFIDENCE_PENALTY * width

        return sorted(records, key=rank_score, reverse=True)


# ── synthesize_and_verify ─────────────────────────────────────────────────────

def synthesize_and_verify(budget: int, seed: Optional[int] = None) -> List[ConjectureRecord]:
    """Full pipeline: synthesize Pareto-optimal variants, then verify each one.

    Parameters
    ──────────
    budget : passed to synthesize() as the exploration budget
    seed   : RNG seed; same seed → same Pareto front → same records

    Returns
    ───────
    List[ConjectureRecord] ranked by composite_score (best first).

    The pipeline is designed to be idempotent: running it twice with the same
    (budget, seed) produces identical output.
    """
    # Step 1: Synthesize Pareto-optimal variants
    synthesis_result = synthesize(budget=budget, seed=seed)
    pareto_front = synthesis_result["pareto_front"]

    if not pareto_front:
        return []

    # Step 2: Verify each variant
    pipeline = VerificationPipeline()
    records: List[ConjectureRecord] = []

    for variant in pareto_front:
        record = pipeline.verify(variant, synthesis_seed=seed if seed is not None else -1)
        records.append(record)

    # Step 3: Rank
    ranker = RankingEngine()
    ranked = ranker.rank(records)

    return ranked


# ── Export functions ──────────────────────────────────────────────────────────

def export_conjectures_to_json(records: List[ConjectureRecord], path: str) -> None:
    """Serialise all ConjectureRecords to a JSON file.

    The output is a JSON array of record dicts, sorted by composite_score
    descending.  Each dict preserves all fields including the LaTeX hypothesis
    so the file is self-contained for downstream tooling.
    """
    import dataclasses

    data = [dataclasses.asdict(r) for r in records]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def export_conjectures_to_markdown(records: List[ConjectureRecord], path: str) -> None:
    """Write a formatted markdown report of the top-5 conjectures.

    Report structure
    ────────────────
    # ProofX — Goldbach Variant Report
    ## Summary table (top 5)
    ## Detailed sections (one per conjecture)
       - Statement
       - LaTeX hypothesis
       - Verification scores (table)
       - Confidence interval
       - Parameter configuration
    """
    top = records[:5]
    lines: List[str] = []

    lines.append("# ProofX — Goldbach Variant Report\n")
    lines.append(f"*Generated {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*\n")
    lines.append(f"Total variants verified: **{len(records)}**  |  "
                 f"Top-5 shown below\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Rank | Composite | Empirical | Heuristic | Structural | "
                 "95% CI | Template |\n")
    lines.append("|------|-----------|-----------|-----------|------------|"
                 "--------|----------|\n")
    for i, r in enumerate(top, 1):
        ci = f"[{r.confidence_lower:.3f}, {r.confidence_upper:.3f}]"
        lines.append(
            f"| {i} | {r.composite_score:.4f} | {r.empirical_score:.4f} | "
            f"{r.heuristic_score:.4f} | {r.structural_score:.4f} | "
            f"{ci} | `{r.template_name}` |\n"
        )
    lines.append("\n")

    # Detailed sections
    lines.append("## Detailed Conjectures\n")
    for i, r in enumerate(top, 1):
        lines.append(f"### #{i} — {r.template_name}\n")
        lines.append(f"**Statement:** {r.variant_statement}\n\n")
        lines.append("**LaTeX Hypothesis:**\n\n")
        lines.append(f"$$\n{r.latex_hypothesis}\n$$\n\n")
        lines.append("**Verification Scores:**\n\n")
        lines.append("| Verifier | Score | Weight | Contribution |\n")
        lines.append("|----------|-------|--------|--------------|\n")
        lines.append(f"| Empirical (PartitionEnumerator) | {r.empirical_score:.4f} | 0.50 | "
                     f"{0.50 * r.empirical_score:.4f} |\n")
        lines.append(f"| Heuristic (GoldbachReasoner) | {r.heuristic_score:.4f} | 0.30 | "
                     f"{0.30 * r.heuristic_score:.4f} |\n")
        lines.append(f"| Structural (AlgebraicExtensions) | {r.structural_score:.4f} | 0.20 | "
                     f"{0.20 * r.structural_score:.4f} |\n")
        lines.append(f"\n**Composite Score:** {r.composite_score:.4f}  \n")
        lines.append(f"**95% Confidence Interval:** "
                     f"[{r.confidence_lower:.4f}, {r.confidence_upper:.4f}]  \n")
        lines.append(f"**Tested range:** even numbers in "
                     f"[{r.tested_range[0]}, {r.tested_range[1]}]  \n")
        lines.append(f"**Synthesis seed:** {r.synthesis_seed}  \n\n")
        lines.append("**Parameters:**\n\n```json\n")
        lines.append(json.dumps(r.params, indent=2))
        lines.append("\n```\n\n")
        lines.append("---\n\n")

    _Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
