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
| `lyapunov_exponent` | Average log growth along the sampled trajectory. | Local diagnostic only. |
| `hurst_exponent` | Persistence estimate for the trajectory. | Sensitive to sequence length. |
| `parity_ratio` | Fraction of odd steps. | A finite prefix can mislead. |
| `growth_rate` | Mean relative ascent per step. | Saturated by large excursions. |
| `binary_entropy` | Entropy proxy from bit representation. | Ranking heuristic, not theorem data. |

### Algebraic Features

| Feature | Meaning |
| --- | --- |
| `mod_6_class` | First-branch residue information. |
| `bit_density` | Fraction of 1 bits in the binary representation. |
| `consecutive_ones` | Longest binary run of 1s. |

## Parity Threshold

The common heuristic threshold comes from the average log multiplier. If `p` is
the long-run fraction of odd steps, contraction requires:

```text
p * log(3) < log(2)
p < log(2) / log(3)
```

This is a heuristic signal for finite trajectories. It is useful for ranking
but cannot certify divergence.

## Rare Events

Stopping-time anchors such as `27`, `703`, `871`, `6171`, `77031`, `837799`,
`8400511`, and `63728127` are useful because their trajectories are unusually
long relative to scale. The directed search expands around these anchors to
spend budget on known anomalous neighborhoods.

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
