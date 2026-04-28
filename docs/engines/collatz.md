# CollatzX Engine

## Conjecture statement

For every positive integer n, repeated application of the map

```
T(n) = n / 2       if n is even
T(n) = 3n + 1      if n is odd
```

eventually reaches 1.

No counterexample has ever been found. Computational verification covers all n < 2⁶⁸
(Oliveira e Silva, 2011).

---

## Module overview

| Module | Purpose |
|--------|---------|
| `Analytics/` | Feature extraction from Collatz sequences |
| `Bifurcation/` | Bifurcation structure of the inverse Collatz tree |
| `Boundary/` | Boundary analysis of convergence basins |
| `Pipeline/` | End-to-end run orchestration |
| `PrimeGraph/` | Graph of prime-to-prime transitions under T |
| `Processing/` | High-throughput sequence computation |
| `RareEvent/` | Statistical detection of anomalous stopping times |

---

## Analytics: feature extraction

`Analytics.py` defines two feature extractors and a `FeatureUnion` combiner.

### StatisticalFeatureExtractor

Operates on the raw integer sequence `[n, T(n), T²(n), …, 1]`:

| Feature | Formula | Interpretation |
|---------|---------|----------------|
| `lyapunov_exponent` | mean(log |T(xᵢ)/xᵢ|) | Average log-expansion; positive → sequence growing locally |
| `hurst_exponent` | R/S rescaled range | H > 0.5 → persistent trend; H < 0.5 → mean-reverting |
| `parity_ratio` | #odd steps / total steps | Should be < log(2)/log(3) ≈ 0.6309 for convergent sequences |
| `growth_rate` | mean((xᵢ₊₁ − xᵢ) / xᵢ) | Normalised mean ascent per step |
| `binary_entropy` | Shannon entropy of the bit string | High entropy → complex bit pattern |

### AlgebraicFeatureExtractor

Operates on the binary representation and residue classes:

| Feature | Description |
|---------|-------------|
| `mod_6_class` | n mod 6 — determines which rule branch applies first |
| `bit_density` | Fraction of 1-bits; proxy for parity_ratio without running the sequence |
| `consecutive_ones` | Longest run of 1s in binary — associated with delayed even-step reduction |

### Convergence threshold

The parity ratio criterion derives from the long-run Lyapunov exponent of the map:

```
λ = k_odd · log(3) + k_total · log(1/2)
  = k_total · [p · log(3) − log(2)]
```

where p = k_odd / k_total. For λ < 0 (sequence contracts on average):

```
p < log(2) / log(3) ≈ 0.6309
```

Empirically, almost all sequences satisfy p < 0.55 comfortably. Sequences with
p close to 0.6309 are the most anomalous — and the most computationally valuable
to study.

---

## PrimeGraph: prime-to-prime transition graph

`PrimeGraph.py` restricts the Collatz map to prime inputs and tracks where each
prime trajectory passes through other primes.

**Graph construction:**

1. For each prime p in the input range, compute the full Collatz trajectory.
2. Extract the subsequence of primes visited: [p, p₁, p₂, …, attractor].
3. Add directed edges p → p₁ → p₂ → … with edge weight = number of trajectories
   using that transition.

**Attractor primes** are primes that are fixed points or cycle minima under T
restricted to ℙ. For standard T (k=3, b=1, d=2), the attractor is 2 (via the
eventual 4 → 2 → 1 collapse, but 2 is the only prime in that sink).

**Research use:** The basin structure of the graph reveals which primes are
"attractors" and how the prime population partitions under the dynamics.

---

## RareEvent: stopping-time anomaly detection

`rareeventx.py` identifies primes (and integers) whose stopping time
σ(n) = min{k : Tᵏ(n) = 1} is anomalously large relative to the expectation
E[σ(n)] ≈ 2 · log₂(n).

**Method:** Fit a log-normal distribution to σ(n) / log₂(n) over a calibration
range, then flag entries whose standardised score exceeds a threshold.

Known record holders (highest stopping times relative to log₂(n)):

| n | σ(n) | σ(n)/log₂(n) |
|---|------|--------------|
| 27 | 111 | 16.8 |
| 703 | 170 | 19.3 |
| 871 | 178 | 19.9 |
| 6 171 | 261 | 22.2 |
| 77 031 | 350 | 21.4 |
| 837 799 | 524 | 26.0 |

These are the FalsificationEngine's beam-search anchors because they represent
the deepest known anomalies in the stopping-time distribution.

---

## Running the pipeline

```bash
# Full pipeline over [1, 100_000]
python -m codebase.CollatzX.Pipeline.pipeline --start 1 --end 100000

# Via unified CLI
python -m codebase.cli collatz --start 1 --end 100000

# FalsificationEngine (directed search, no brute-force scan)
python -m codebase.cli falsify --budget 500 --seed 42 --target collatz
```
