# FalsificationEngine

The FalsificationEngine coordinates directed counterexample search. It ranks
candidates, evaluates them, and records what happened in a JSONL ledger.

It does not prove conjectures. A run that finds no counterexample should be
reported as **unrefuted at this budget**.

## Purpose

The engine exists for cases where a uniform scan is either too expensive or not
the most interesting use of a limited budget. Instead of asking "did every
integer below N pass?", it asks:

```text
Given a finite budget, which candidates look structurally closest to a
counterexample under the assumptions encoded in this engine?
```

The output is a ranked set of checked candidates plus the full evaluation
ledger. That ledger is the research object.

## Run Semantics

| Term | Meaning |
| --- | --- |
| `budget` | Number of candidate evaluations allocated to one or more targets. |
| `target` | `collatz`, `goldbach`, `riemann`, or a combined run. |
| `seed` | Master RNG seed used to derive deterministic child seeds. |
| `near_miss_score` | Strategy-specific ranking score in `[0, 1]`. |
| `ledger` | Append-only record of every evaluated candidate. |

Scores are comparable inside a strategy. They are not calibrated probabilities,
and a high score does not imply a candidate is close to a true counterexample in
any theorem-level sense.

## Architecture

```text
FalsificationEngine
  CollatzFalsifier
    inverse-tree beam search
    residue-class neighborhood expansion
    feature extraction
    near-miss ranking

  GoldbachFalsifier
    sparse-family candidate generation
    partition counting
    Hardy-Littlewood deficit scoring
    structural hardness scoring

  RiemannFalsifier
    numerical zeta-zero diagnostics
    Keiper-Li coefficient diagnostics

  FalsificationLedger
    append-only entries
    top-k retrieval
    JSONL export
```

## Ledger Schema

Each row is one evaluated candidate:

```json
{
  "candidate": 12345,
  "conjecture": "collatz",
  "strategy": "inverse_tree_beam_search",
  "features": {
    "lyapunov_exponent": 0.0412,
    "hurst_exponent": 0.5831,
    "parity_ratio": 0.5714
  },
  "near_miss_score": 0.2847,
  "details": {
    "stopping_time": 88,
    "max_value": 56320,
    "converged": 1
  },
  "timestamp": 1714300000.0,
  "rng_seed": 1234567890
}
```

Use the ledger when reviewing a run. Summaries and top-k tables are convenience
views only.

## Collatz Scoring

The Collatz ranker combines a feature-based risk score with an excursion bonus:

```text
near_miss = 0.70 * risk_score + 0.30 * excursion_bonus
```

`risk_score` is a weighted sum:

| Feature | Weight | Normalization | Reason |
| --- | ---: | --- | --- |
| `lyapunov_exponent` | 0.35 | positive values clipped to `[0, 1]` | Local average expansion. |
| `hurst_exponent` | 0.25 | `max(0, H - 0.5) * 2` | Persistent upward trend. |
| `parity_excess` | 0.20 | excess over `log(2) / log(3)` | Odd-step fraction above contraction threshold. |
| `binary_entropy` | 0.10 | clipped entropy proxy | Bit-pattern complexity. |
| `growth_rate` | 0.10 | absolute value clipped to `[0, 1]` | Mean ascent per step. |

The weights are asserted to sum to 1.0 in code. If a weight changes, update this
document and the tests or assertions that defend the scoring contract.

### Inverse-Tree Search

The inverse Collatz map gives at most two predecessors for `n`:

1. `2n`, because `T(2n) = n`.
2. `(n - 1) / 3`, when this is an odd integer greater than 1.

The search starts from known high stopping-time anchors and expands backward.
This concentrates evaluations around trajectories that already have unusually
long transients.

The queue is gated by a cheap bit-level proxy so the doubling chain does not
consume the whole budget.

## Goldbach Scoring

The Goldbach ranker uses a Hardy-Littlewood deficit plus a smaller structural
hardness term:

```text
near_miss = 0.85 * deficit + 0.15 * structural_hardness
deficit = 1 - G(n) / predicted_G(n)
```

`G(n)` is the number of prime pairs `(p, q)` with `p + q = n` and `p <= q`.

The ranker favors structurally sparse families, such as powers of two, `2p`
with large prime `p`, and residue classes with fewer allowed prime-pair
combinations. These families are useful because they tend to have lower
predicted partition counts relative to scale.

If `G(n) = 0`, the candidate is a potential counterexample and needs independent
review of the enumeration path, prime source, and input range.

## Riemann Diagnostics

`RiemannFalsifier` is numerical. It computes zeta-zero and Keiper-Li signals and
records deviations or anomalies. These outputs are diagnostics, not certified
proof artifacts. Floating-point precision, library behavior, and numerical
method details matter.

Do not present Riemann diagnostics as proof that zeros lie on the critical line.

## Reproducibility

Run output depends on:

- code revision;
- Python version;
- dependency versions;
- platform math libraries;
- command, target, budget, and seed;
- any ledger post-processing.

The engine derives child seeds from a master seed:

```python
rng_master = np.random.default_rng(seed)
collatz_seed, goldbach_seed = rng_master.integers(0, 2**31, size=2)
```

When publishing a run, include the command and ledger:

```bash
python -m codebase.cli falsify \
    --budget 2000 \
    --seed 42 \
    --target both \
    --save-ledger results/ledger.jsonl \
    --output-json results/summary.json
```

## Public Reporting Template

Use this wording:

```text
This run evaluated <N> candidates using <strategy> at seed <seed>.
No counterexample was found within the configured budget.
The top rows are near-miss candidates under ProofX's ranking function;
they are not evidence that the conjecture is true or false.
```

Avoid:

- "verified the conjecture";
- "proved no counterexample exists";
- "proof-grade result";
- "guaranteed identical across environments" without a pinned environment.
