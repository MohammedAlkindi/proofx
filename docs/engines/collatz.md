# CollatzX

CollatzX contains utilities for studying Collatz trajectories and feeding
trajectory features into the FalsificationEngine.

It does not prove the Collatz conjecture. It computes bounded trajectories,
features, and search ledgers.

## Conjecture

For every positive integer `n`, repeated application of

```text
T(n) = n / 2       if n is even
T(n) = 3n + 1      if n is odd
```

eventually reaches 1.

No counterexample is known. ProofX should only claim what its own runs check.

## Module Map

| Module | Purpose |
| --- | --- |
| `Analytics/` | Sequence construction and feature extraction. |
| `Bifurcation/` | Experiments on inverse-tree structure. |
| `Boundary/` | Boundary and basin experiments. |
| `Pipeline/` | Higher-level run orchestration. |
| `PrimeGraph/` | Prime-to-prime transitions seen inside trajectories. |
| `Processing/` | Speed-oriented sequence computation helpers. |
| `RareEvent/` | Stopping-time anomaly analysis. |

Some modules are exploratory and are not part of the root CLI's core run path.
Check tests and imports before treating a module as production code.

## Feature Extraction

`Analytics.py` exposes statistical and algebraic features used by the
FalsificationEngine.

### Statistical Features

| Feature | Meaning | Caveat |
| --- | --- | --- |
| `lyapunov_exponent` | Mean log ratio over the first nine transitions; zero for paths shorter than ten values. | A short-prefix diagnostic, not an asymptotic Lyapunov exponent. |
| `hurst_exponent` | Persistence estimate for the trajectory. | Sensitive to sequence length. |
| `parity_ratio` | Odd fraction among transition origins, excluding the last recorded value. | Zero for paths with no transitions. A finite prefix can mislead. |
| `growth_rate` | Mean signed difference divided by the path maximum (plus a numerical epsilon). | Telescopes to net displacement divided by transition count and maximum; not mean ascent. |
| `binary_entropy` | Mean Bernoulli bit entropy over positive path values. | Ranking heuristic, not theorem data. |

### Algebraic Features

| Feature | Meaning |
| --- | --- |
| `mod_6_class` | First-branch residue information. |
| `bit_density` | Fraction of 1 bits in the binary representation. |
| `consecutive_ones` | Longest binary run of 1s. |

## Parity Threshold

For the ordinary map used here, the leading log multiplier for odd-transition
fraction `p` is:

```text
p * log(3) - (1 - p) * log(2)
zero at p = log(2) / log(6) = 0.38685...
```

The threshold `log(2) / log(3)` belongs to the shortcut map whose odd step is
`(3n + 1) / 2`. Mixing that convention with the ordinary map is incorrect.

For a completed ordinary path from `n > 1` to `1`, let `o` and `e` count odd
and even transitions. Exact multiplication gives

```text
-log(n) = o*log(3) - e*log(2) + sum_odd log(1 + 1/(3*n_i)).
```

The correction sum is nonnegative, so `o/(o+e) < log(2)/log(6)`.
The full-path parity-excess score is therefore always zero on these completed
paths, even with the corrected convention. It supplies no discrimination among
them. Any future prefix-based predictor needs a separate prospective study.
No threshold here certifies divergence or calibrates a counterexample probability.

The queue's input-bit reference remains `log(2)/log(3)` solely to preserve
historical selection behavior. It is an unvalidated ranking parameter and has
no orbit-contraction interpretation. Updated ledgers identify the feature
convention as `details.score_version = collatz.ordinary.transitions.v2`.

## Rare Events

Stopping-time anchors such as `27`, `703`, `871`, `6171`, `77031`, `837799`,
`8400511`, and `63728127` are useful because their trajectories are unusually
long relative to scale. The directed search expands around these anchors to
spend budget on known anomalous neighborhoods.

Inverse predecessors of a known convergent anchor are themselves convergent.
The residue-neighborhood branch adds other inputs. Queue order uses the cheap
input-bit score; full trajectory scores rank the output ledger, without feeding
back into selection. The former dynamic-refresh branch could not reinsert any
ledger entry because every such candidate was already marked visited.

## Browser Demo

The public Collatz demo is an in-browser tracer. It is capped for responsiveness
and should not be described as the full engine or as a verification system.

## Commands

```bash
# Unified CLI, directed search
python -m codebase.cli falsify --budget 500 --seed 42 --target collatz

# Save a ledger
python -m codebase.cli falsify \
    --budget 500 \
    --seed 42 \
    --target collatz \
    --save-ledger results/collatz.jsonl
```

## Reporting Standard

Good:

```text
No counterexample was found among candidates evaluated by this seeded run.
The highest-ranked candidate converged to 1 after <steps> steps.
```

Avoid:

```text
CollatzX verifies the Collatz conjecture.
```
