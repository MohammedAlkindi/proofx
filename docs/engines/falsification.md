# FalsificationEngine

## Purpose

The FalsificationEngine is ProofX's core research tool. Rather than scanning ℕ
uniformly — which wastes compute on numbers that trivially satisfy each conjecture
— it applies *directed* search strategies that concentrate the evaluation budget
on candidates most likely to be counterexamples.

It produces a structured JSONL ledger of every evaluation, with near-miss scores,
full feature vectors, and reproducibility metadata.

---

## Design philosophy

Uniform (brute-force) scanning has verified both conjectures up to enormous
bounds. The remaining open question is not "does a counterexample exist below
10^N?" but "what mathematical structure would a counterexample have if it
existed?" The FalsificationEngine operationalises that question.

Each search strategy is derived from a mathematical argument for *why* certain
candidate families are structurally closer to being counterexamples:

- **Collatz:** A non-converging number would have an anomalously high Lyapunov
  exponent, a persistent upward trend (Hurst > 0.5), and a parity ratio above
  the convergence threshold log(2)/log(3) ≈ 0.6309. Candidates with these
  properties are found by expanding backward from known champions (27, 703, …).

- **Goldbach:** An even number with no prime partition would have a Hardy-
  Littlewood deficit of 1. Numbers closest to this are those with the smallest
  predicted partition count — powers of 2 and numbers avoiding small odd prime
  factors.

---

## Architecture

```
FalsificationEngine
├── CollatzFalsifier
│   ├── Inverse-tree beam search (anchored at stopping-time champions)
│   ├── Residue-class neighbourhood expansion (preserves mod-6 structure)
│   ├── FeatureUnion (StatisticalFeatureExtractor + AlgebraicFeatureExtractor)
│   └── Near-miss score = 0.7 × risk + 0.3 × excursion_bonus
│
├── GoldbachFalsifier
│   ├── Hardy-Littlewood deficit search (structurally sparse families)
│   ├── Algebraic hardness bonus (mod_class_prune + composite_precheck)
│   └── Near-miss score = 0.85 × deficit + 0.15 × hardness
│
├── FalsificationLedger
│   ├── Append-only list of LedgerEntry records
│   ├── Max-heap over near_miss_score for O(k log n) top-k queries
│   └── JSONL serialisation
│
└── FalsificationEngine.run()
    ├── Derives independent child seeds from master seed (reproducibility)
    ├── Splits budget evenly between engines
    ├── Merges ledgers into a single ranked output
    └── Returns stats dict + top-k lists per conjecture
```

---

## Near-miss score derivation

### Collatz risk score

The risk score is a weighted sum of five normalised features:

| Feature | Weight | Normalisation | Rationale |
|---------|--------|--------------|-----------|
| `lyapunov_exponent` | 0.35 | max(0, raw) → [0,1] | Primary divergence signal |
| `hurst_exponent` | 0.25 | max(0, H − 0.5) × 2 | Persistent growth trend |
| `parity_excess` | 0.20 | (ratio − 0.6309) / (1 − 0.6309) | Above convergence threshold |
| `binary_entropy` | 0.10 | raw / log₂(seq_len) | Complex bit structure |
| `growth_rate` | 0.10 | abs(rate), clipped to [0,1] | Mean ascent per step |

Weights sum to exactly 1.0 (asserted at class load time).

The final **near-miss score** blends the risk score with an excursion bonus:

```
near_miss = 0.7 × risk + 0.3 × excursion_bonus
```

where `excursion_bonus` measures how far above its starting value the sequence
climbed, normalised by the expected stopping time. A sequence that reaches
1000× its starting value before descending scores near 1.0 on excursion.

### Goldbach deficit score

```
near_miss = 0.85 × deficit + 0.15 × structural_hardness

deficit = 1 − G(n) / G̃(n)
structural_hardness = 0.6 × residue_score + 0.4 × warning_score
```

The 85/15 split reflects that the Hardy-Littlewood deficit is the primary
signal; the algebraic hardness is a tie-breaker among candidates with equal
deficits.

---

## Reproducibility guarantee

All randomness flows through a single seeded `np.random.Generator`. Given seed
`s`, the search path is identical across Python versions (for a fixed NumPy
version) and machines. Child seeds for each sub-engine are derived
deterministically from the master seed so that running with `--target collatz`
produces the same Collatz results as `--target both` at the same master seed.

```python
rng_master = np.random.default_rng(seed)
child_seeds = rng_master.integers(0, 2**31, size=2)
collatz_seed, goldbach_seed = child_seeds[0], child_seeds[1]
```

---

## Ledger schema

Each line of the JSONL ledger is one JSON object:

```json
{
  "candidate":       12345,
  "conjecture":      "collatz",
  "strategy":        "inverse_tree_beam_search",
  "features": {
    "lyapunov_exponent": 0.0412,
    "hurst_exponent":    0.5831,
    "parity_ratio":      0.5714,
    "binary_entropy":    0.9912,
    "growth_rate":       0.0031
  },
  "near_miss_score": 0.2847,
  "details": {
    "stopping_time":          88,
    "max_value":           56320,
    "sequence_length":        89,
    "converged":               1,
    "cycle_detected":          0,
    "computation_time_s":  0.0003,
    "expected_stopping_time": 27.6
  },
  "timestamp":  1714300000.0,
  "rng_seed":   1234567890
}
```

---

## Inverse-tree beam search (Collatz)

### Why inverse-tree, not forward scan?

The inverse Collatz tree rooted at any champion seed clusters **all** numbers
that visit that seed's risky trajectory. Expanding backward concentrates the
budget on this cluster rather than uniformly sampling ℕ.

### Inverse map

Every integer n has at most two predecessors under T:

1. **Even inverse:** 2n — because T(2n) = 2n/2 = n.
2. **Odd inverse:** (n − 1)/3 — because T(m) = 3m + 1 = n implies m = (n−1)/3.
   Valid only when (n − 1) ≡ 0 (mod 3) and (n−1)/3 is odd and > 1.

### Residue-class neighbourhood

Numbers sharing n mod 6 with a high-risk candidate have the same first branch
under T (all n ≡ 1 (mod 6) reach 4 (mod 6) in one odd step, etc.). The engine
samples nearby numbers in the same residue class as a cheap diversification step.

### Queue admission

A cheap bit-level proxy score (bit density + Shannon entropy of bits) gates
which predecessors are admitted to the priority queue. This avoids bloat from
the unbounded doubling chain 2n → 4n → 8n → … while still exploring the
structurally interesting predecessors.

---

## CLI reference

```
python -m codebase.cli falsify [OPTIONS]

Options:
  --budget INT       Total evaluation budget (default 200)
  --seed INT         Master RNG seed (default 42)
  --target STR       collatz | goldbach | both (default both)
  --top-k INT        Near-misses to print per conjecture (default 5)
  --save-ledger PATH Save full JSONL ledger
  --output-json PATH Save JSON summary report
  --log-level STR    DEBUG | INFO | WARNING | ERROR (default INFO)
```

### Workflow for a research run

```bash
# 1. Run search, save ledger
python -m codebase.cli falsify \
    --budget 2000 --seed 42 --target both \
    --save-ledger results/ledger.jsonl \
    --output-json results/summary.json

# 2. Open ledger in the interactive viewer
open public/ledger-viewer.html   # drop results/ledger.jsonl onto it

# 3. Label top entries manually (add "label": 0 or 1 to each line)
# 4. Fit a calibrator
python -m codebase.cli calibrate fit \
    --ledger results/ledger_labelled.jsonl \
    --method isotonic \
    --output results/calibrator.pkl

# 5. Annotate the full ledger with calibrated probabilities
python -m codebase.cli calibrate annotate \
    --ledger results/ledger.jsonl \
    --calibrator results/calibrator.pkl

# 6. Run cross-engine correlation
python -m codebase.cli correlate \
    --collatz results/collatz.jsonl \
    --goldbach results/goldbach.jsonl \
    --radius 200 \
    --output-json results/correlation.json
```

---

## Extending the engine

### Adding a RiemannFalsifier

The `ReimannX` module (ContourTruth, KeiperLi, ZetaMirror) provides the
computational substrate. A `RiemannFalsifier` class should:

1. Search for Riemann zeros with `|Re(s) − 0.5| > ε` using contour integration
   (ZetaMirror provides a starting point).
2. Score candidates by the distance of the computed zero from the critical line.
3. Record to `FalsificationLedger` with `conjecture="riemann"`.
4. Plug into `FalsificationEngine.run()` alongside the existing two falsifiers.

### Parallel execution

Both `CollatzFalsifier.search()` and `GoldbachFalsifier.search()` are CPU-bound
and independent. Wrapping them in `concurrent.futures.ProcessPoolExecutor`
reduces wall-clock time by ~50 % on a dual-core machine:

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=2) as ex:
    f_cz = ex.submit(self._collatz.search, half, collatz_seed)
    f_gb = ex.submit(self._goldbach.search, budget - half, goldbach_seed)
    collatz_ledger = f_cz.result()
    goldbach_ledger = f_gb.result()
```
