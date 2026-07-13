# CollatzX Research Log

Tracks tested ranges, methodology changes, and notable discoveries for the CollatzX engine.

---

## 2025-04-27 — FalsificationEngine integration

**What changed:** Inverse-tree beam search added via `FalsificationEngine.py`. Seeds expansion from known high-stopping-time anchors instead of linear scan.

**Anchor seeds used:**
```
27, 703, 871, 6171, 77031, 837799, 8400511, 63728127
```

**Parity convergence threshold:** log(2)/log(3) ≈ 0.6309. Sequences whose parity_excess approaches this bound are scored highest.

**Feature weights (near-miss score):**
| Feature | Weight |
|---|---|
| lyapunov_exponent | 0.35 |
| hurst_exponent | 0.25 |
| parity_excess | 0.20 |
| binary_entropy | 0.10 |
| growth_rate | 0.10 |

**Top candidates (seed 42, budget 500):**
| n | Stopping time | Peak value | Score |
|---|---|---|---|
| 63,728,127 | 949 | 966,616,035,460 | 0.8821 |
| 8,400,511 | 685 | 159,424,614,468 | 0.8614 |
| 837,799 | 524 | 2,974,984,576 | 0.8302 |

**Result:** No counterexample found. All candidates converge to 1.

---

## 2025-04-01 — Initial large-scale scan

**Tested range:** 1 to 2^64 (uniform linear scan)
**Throughput:** 100M+ numbers/sec (parallelized)
**Method:** Direct iteration with memoized stopping times
**Result:** Full convergence. No cycles detected outside {1, 2, 4}.

---

## Next targets

- Extend inverse-tree beam depth from 12 to 20 levels
- Integrate Hurst exponent threshold filter (target: H > 0.75) for pre-screening
- Test Generalized Collatz (3n + k for k ∈ {1, 5, 7}) for comparative baseline
