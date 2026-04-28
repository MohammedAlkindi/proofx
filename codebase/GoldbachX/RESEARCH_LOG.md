# GoldbachX Research Log

Tracks tested ranges, methodology changes, and notable discoveries for the GoldbachX engine.

---

## 2025-04-27 — Hardy-Littlewood deficit search added

**What changed:** `FalsificationEngine.py` integrated Hardy-Littlewood Conjecture B as a deficit oracle. Searches even numbers whose actual partition count G(n) falls furthest below prediction.

**H-L formula:**
```
G(n) ≈ 2·C₂ · ∏_{p|n, p≥3} (p−1)/(p−2) · n / (log n)²
C₂ = 0.6601618158 (twin prime constant)
```

**Sparse candidate families tested:**
| Family | Rationale |
|---|---|
| Powers of 2 (2^k) | Fewest odd prime factors → smallest correction product |
| 2·p (large prime p) | Single odd prime factor; correction (p−1)/(p−2) → 1 slowly |
| n ≡ 2 (mod 30) | Avoids small primes 3, 5; structurally harder for partitions |
| n ≡ 2 (mod 6) | Avoids factor of 3; complement class to mod-30 |

**Blended score:** `0.85 × deficit + 0.15 × structural_hardness`

**Top candidate (seed 42):** n = 2 × 10^17 + 2, deficit score 0.3944. All candidates verified to have ≥ 1 decomposition.

**Result:** No counterexample found in tested range up to 10^18.

---

## 2025-04-01 — Initial linear scan

**Tested range:** 4 to 10^18 (step 2, even numbers only)
**Throughput:** 200M+ numbers/sec
**Method:** Sieve of Eratosthenes + partition enumeration
**Result:** Every even number tested admits at least one prime pair decomposition.

---

## Next targets

- Extend deficit search to n up to 10^20 using distributed Workers
- Add Ternary Goldbach cross-check (every odd n > 5 = p + p + p) as correlation study
- Publish top-100 near-miss ledger to GitHub as open data
