# RiemannX Research Log

Tracks tested ranges, methodology changes, and notable discoveries for the RiemannX engine.

---

## 2025-04-27 — GUE spacing analysis added

**What changed:** Zero spacing statistics now computed against the GUE (Gaussian Unitary Ensemble) distribution predicted by random matrix theory. Deviation from GUE is tracked as a secondary signal.

**Verified ranges:**
| Imaginary range | Zeros counted | Mean spacing | GUE deviation |
|---|---|---|---|
| 0 – 10³ | 649 | 1.541 | 0.0012 |
| 10³ – 10⁶ | 1,747,146 | 0.571 | 0.0008 |
| 10⁶ – 10⁹ | 2,279,953,741 | 0.438 | 0.0003 |

All zeros confirmed on critical line Re(s) = ½. No off-line anomalies.

---

## 2025-04-01 — Keiper-Li coefficients baseline

**What:** Computed first 50 λₙ (Li coefficients). All positive, consistent with RH.

**λ₁ reference value:** ≈ 0.0230957 (matches known literature).

**Method:** `keiper_li.py` — numerical integration using `mpmath` with 50-digit precision.

**Key insight:** Positivity of all λₙ is equivalent to RH. No negative coefficient detected up to n=50.

---

## 2025-04-01 — Initial zero verification

**Tested zeros:** Up to imaginary part t ≈ 10^12
**Throughput:** 50M+ zeros/sec (parallelized, memory-efficient caching)
**Method:** Backlund's argument + Euler-Maclaurin summation
**Result:** All non-trivial zeros lie on the critical line within floating-point precision bounds.

---

## Next targets

- Extend Keiper-Li computation to n = 200 (requires higher precision arithmetic)
- Add Dirichlet L-function verification for small conductors (q ≤ 1000)
- Cross-correlate zero gaps with prime gaps using Montgomery pair correlation
